"""Diagnóstico descartável: mede em que POSIÇÃO (rank) o chunk correto
aparece na busca híbrida real, sem filtro por documento — a mesma condição
real de `orquestracao/nos/pesquisador_legal.py` (limit=5, sem
`documento_id`), não a condição facilitada de `verificar_busca_hibrida.py`
(Bloco A filtra por documento).

Pergunta que este script responde: quantas consultas reais teriam o
dispositivo correto FORA do limit=5 que o `pesquisador_legal` de fato usa
hoje? Isso mede se um reranking de segundo estágio traria ganho real, antes
de gastar esforço implementando — só leitura, nunca escreve no Qdrant.

Roda só via workflow_dispatch, nunca local (mesma disciplina de todo script
de infraestrutura real deste projeto).
"""

import os
import sys

LIMIT_PRODUCAO = 5
LIMIT_MEDICAO = 20
N_CHUNKS_TESTE = 20
PALAVRAS_DO_TRECHO = 12


def _falhar(msg: str) -> None:
    print(f"FALHA: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    from qdrant_client import QdrantClient

    from ingestion.embedding.hybrid_embedder import (
        MODELO_DENSO_PADRAO,
        FastEmbedHybridEmbedder,
    )
    from ingestion.indexing.qdrant_indexer import QdrantIndexer

    url = os.environ["QDRANT_URL"]
    api_key = os.environ["QDRANT_API_KEY"]
    collection = os.environ.get("QDRANT_COLLECTION_NAME", "legislacao_tributaria")

    client = QdrantClient(url=url, api_key=api_key)
    indexer = QdrantIndexer(url=url, api_key=api_key, collection_name=collection)
    embedder = FastEmbedHybridEmbedder(
        dense_model_name=os.environ.get("DENSE_EMBEDDING_MODEL", MODELO_DENSO_PADRAO)
    )

    total = client.count(collection_name=collection, exact=True).count
    print(f"Coleção '{collection}': {total} pontos indexados\n")
    if total == 0:
        _falhar("coleção vazia")

    amostra, offset = [], None
    while len(amostra) < 400:
        pontos, offset = client.scroll(
            collection_name=collection, limit=200, offset=offset, with_payload=True
        )
        amostra.extend(pontos)
        if offset is None:
            break

    candidatos = [
        p for p in amostra if p.payload and len((p.payload.get("texto") or "").split()) >= PALAVRAS_DO_TRECHO * 2
    ]
    if len(candidatos) < N_CHUNKS_TESTE:
        _falhar(f"apenas {len(candidatos)} chunks longos o bastante (mínimo {N_CHUNKS_TESTE})")

    passo = max(1, len(candidatos) // N_CHUNKS_TESTE)
    selecionados = [candidatos[i * passo] for i in range(N_CHUNKS_TESTE)]

    posicoes: list[int | None] = []
    print(f"=== Posição real do chunk correto, sem filtro de documento (limit={LIMIT_MEDICAO}) ===\n")
    for i, ponto in enumerate(selecionados, 1):
        payload = ponto.payload or {}
        dispositivo = payload.get("dispositivo", "?")
        documento = payload.get("documento_id", "?")
        palavras = (payload.get("texto") or "").split()
        meio = len(palavras) // 3
        consulta = " ".join(palavras[meio : meio + PALAVRAS_DO_TRECHO])

        emb = embedder.embed_consulta(consulta)
        resultado = indexer.search_hybrid(
            dense_query=emb.dense_vector,
            sparse_indices=emb.sparse_indices,
            sparse_values=emb.sparse_values,
            limit=LIMIT_MEDICAO,
        )
        ids = [str(p.id) for p in resultado.points]
        try:
            posicao = ids.index(str(ponto.id)) + 1
        except ValueError:
            posicao = None

        posicoes.append(posicao)
        marca = "dentro do limit=5 real" if posicao is not None and posicao <= LIMIT_PRODUCAO else "FORA do limit=5 real"
        print(f"  [{i:2d}/{N_CHUNKS_TESTE}] [{documento}] {dispositivo}: posição {posicao or f'>{LIMIT_MEDICAO}'} — {marca}")

    dentro_producao = sum(1 for p in posicoes if p is not None and p <= LIMIT_PRODUCAO)
    posicao_1 = sum(1 for p in posicoes if p == 1)
    fora_top20 = sum(1 for p in posicoes if p is None)

    print("\n" + "=" * 60)
    print(f"No topo (posição 1): {posicao_1}/{N_CHUNKS_TESTE}")
    print(f"Dentro do limit={LIMIT_PRODUCAO} real do pesquisador_legal: {dentro_producao}/{N_CHUNKS_TESTE}")
    print(f"Fora do top-{LIMIT_MEDICAO} inteiro: {fora_top20}/{N_CHUNKS_TESTE}")
    print(
        f"\nSe um reranker pegasse os {LIMIT_MEDICAO} candidatos e reordenasse com precisão, "
        f"o ganho potencial é de até {N_CHUNKS_TESTE - dentro_producao} consulta(s) desta amostra "
        "que hoje ficam fora do que o LLM realmente vê."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — borda de CLI, qualquer falha vira exit 1 com mensagem
        print(f"FALHA: {exc}", file=sys.stderr)
        sys.exit(1)
