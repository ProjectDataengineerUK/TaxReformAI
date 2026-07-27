"""Ingere as resoluções do CGIBS ainda não indexadas.

A nº 6 (a que regulamenta o IBS, 617 artigos) já foi ingerida separadamente —
reingeri-la aqui custaria ~20 min de embedding sem ganho, já que o point id
do Qdrant é o mesmo. `PULAR_POR_PADRAO` existe para isso, não para esconder
falha: se a nº 6 precisar ser reingerida (ex.: o texto mudou), rode
`ingestion.pipeline run --fonte cgibs` diretamente para ela.

As outras 12 são regimentos, orçamento e afins — baixo valor para o motor de
cálculo, mas completam a cobertura do CGIBS que o blueprint pede (seção 4.1).

Roda só via `ingestao.yml` (guarda `INGERIR`), nunca local.
"""

import os
import sys
import time

import httpx

from ingestion.config import Settings
from ingestion.embedding.hybrid_embedder import FastEmbedHybridEmbedder
from ingestion.indexing.qdrant_indexer import QdrantIndexer
from ingestion.parser.resolucao_parser import parse_resolucao
from ingestion.pipeline import executar_pipeline
from ingestion.scraper.cgibs_scraper import (
    URL_LISTAGEM,
    CGIBSScraper,
    extrair_data_vigencia,
    listar_resolucoes,
)
from ingestion.scraper.planalto_scraper import _HEADERS, decodificar_resposta
from ingestion.storage.raw_storage import GCSRawStorage

PULAR_POR_PADRAO = {6}

# Intervalo entre downloads: a segunda execução real teve 3 ConnectionRefused
# seguidos (nº 10, 11, 12) logo depois de 9 downloads em sequência rápida —
# o próprio servidor respondeu 200 rápido quando testado isoladamente minutos
# depois, então é bloqueio por taxa de requisição, não instabilidade aleatória
# nem URL quebrada. Um intervalo educado é a correção certa, não só a mais
# fácil: bater um servidor público sem pausa é mau comportamento de scraper
# mesmo quando "funciona".
INTERVALO_ENTRE_DOWNLOADS_SEGUNDOS = 5


def main() -> None:
    settings = Settings.from_env()

    resposta = httpx.get(URL_LISTAGEM, headers=_HEADERS, timeout=30, follow_redirects=True)
    resposta.raise_for_status()
    html = decodificar_resposta(resposta.charset_encoding, resposta.content)

    # CGIBS_PULAR sobrepõe PULAR_POR_PADRAO para reprocessar só um subconjunto
    # (ex.: depois de uma falha parcial, sem reincidir sobre o que já ingeriu
    # com sucesso e voltar a martelar o servidor deles). Sem a variável,
    # comportamento padrão continua: só pula a nº 6.
    # `or None` normaliza string vazia para None: o workflow sempre passa a
    # variável de ambiente, mesmo quando o input fica no default "" — sem
    # isso, `pular_override is not None` seria verdadeiro para "" e o parsing
    # devolveria um conjunto vazio, deixando de pular até a nº 6.
    pular_override = os.environ.get("CGIBS_PULAR") or None
    pular = (
        {int(n) for n in pular_override.split(",") if n.strip()}
        if pular_override is not None
        else PULAR_POR_PADRAO
    )
    resolucoes = [r for r in listar_resolucoes(html) if r.numero not in pular]
    print(f"Resoluções a ingerir: {[r.numero for r in resolucoes]}")

    storage = GCSRawStorage(
        bucket_name=settings.gcs_bucket_name, project_id=settings.gcp_project_id
    )
    embedder = FastEmbedHybridEmbedder(dense_model_name=settings.dense_embedding_model)
    indexer = QdrantIndexer(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection_name=settings.qdrant_collection_name,
    )

    falhas = []
    for indice, resolucao in enumerate(resolucoes):
        if indice > 0:
            time.sleep(INTERVALO_ENTRE_DOWNLOADS_SEGUNDOS)
        data_vigencia = extrair_data_vigencia(resolucao)
        if data_vigencia is None:
            # Melhor pular uma resolução do que inventar a data em que ela
            # passou a valer — mas registra alto, não engole em silêncio.
            print(
                f"AVISO: resolução {resolucao.numero} sem data extraível do título "
                f"nem da URL ({resolucao.titulo!r}) — pulando.",
                file=sys.stderr,
            )
            falhas.append(resolucao.numero)
            continue

        scraper = CGIBSScraper(
            storage,
            timeout_seconds=settings.request_timeout_seconds,
            max_retries=settings.max_retries,
        )
        print(f"--- Resolução {resolucao.numero} ({data_vigencia}) ---")
        try:
            resumo = executar_pipeline(
                url=resolucao.url,
                documento_id=resolucao.documento_id,
                titulo=resolucao.titulo,
                esfera="SUBNACIONAL_IBS",
                data_vigencia_inicio=data_vigencia,
                scraper=scraper,
                embedder=embedder,
                indexer=indexer,
                parser=parse_resolucao,
            )
        except Exception as exc:  # noqa: BLE001 — uma resolução com timeout de
            # rede (visto na prática: ConnectTimeout na nº 11) não pode
            # abortar as demais 12. Sem este try/except, a primeira falha
            # transiente derruba o lote inteiro e as resoluções seguintes
            # nunca chegam a ser tentadas — foi exatamente o que aconteceu na
            # primeira execução real deste script.
            print(f"  FALHA na resolução {resolucao.numero}: {exc}", file=sys.stderr)
            falhas.append(resolucao.numero)
            continue
        print(f"  {resumo}")

    if falhas:
        print(f"FALHA: {len(falhas)} resolução(ões) não ingeridas: {falhas}", file=sys.stderr)
        sys.exit(1)

    print(f"OK: {len(resolucoes)} resoluções ingeridas.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — borda de CLI, qualquer falha vira exit 1 com mensagem
        print(f"FALHA: {exc}", file=sys.stderr)
        sys.exit(1)
