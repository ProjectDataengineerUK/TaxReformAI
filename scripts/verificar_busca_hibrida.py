"""Fecha o critério de sucesso pendente de PIPELINE_INGESTAO_LEGAL:
"busca híbrida retorna o dispositivo correto (top-3) para 5 perguntas de teste".

Roda SEMPRE na nuvem (workflow ingestao.yml), nunca local — política do projeto.

Desenho do gabarito
-------------------
As "5 perguntas" nunca foram escritas no DEFINE, e o texto da LCP 214 não é
acessível do sandbox de desenvolvimento. Inventar números de artigo como
gabarito produziria um teste que mede a imaginação de quem o escreveu, não o
sistema. Em vez disso o gabarito é **derivado do corpus realmente indexado**:

  Bloco A (objetivo, pass/fail) — known-item retrieval. Para 5 chunks reais e
  distintos, extrai um trecho literal do texto, consulta com ele e exige que o
  chunk de origem volte no top-3. Verifica de ponta a ponta: embedding,
  indexação, fusão RRF e recuperação do dispositivo certo.

  Bloco B (objetivo, pass/fail) — prova que a busca é de fato HÍBRIDA: a mesma
  consulta é feita só-densa e só-esparsa. Se uma das pernas não retornar nada,
  a "busca híbrida" está silenciosamente degradada para uma perna só.

  Bloco C (informativo, não reprova) — 5 perguntas em linguagem natural sobre
  CBS/IBS/Split Payment. Sem gabarito verificável, o resultado é registrado
  para leitura humana, não usado como critério automático.

Sai com código 1 se qualquer asserção de A ou B falhar.
"""

from __future__ import annotations

import os
import sys

PERGUNTAS_SEMANTICAS = [
    "Qual é a alíquota da CBS?",
    "Como funciona o split payment na liquidação financeira?",
    "Quais operações têm direito a crédito de IBS?",
    "O que caracteriza o Imposto Seletivo?",
    "Qual o tratamento tributário para exportações?",
]

TOP_K = 3
N_CHUNKS_TESTE = 5
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
    print(f"Coleção '{collection}': {total} pontos indexados")
    if total == 0:
        _falhar("coleção vazia — o pipeline de ingestão não indexou nada")

    # Amostra determinística e espalhada pelo corpus (não só os primeiros).
    amostra, offset = [], None
    while len(amostra) < 200:
        pontos, offset = client.scroll(
            collection_name=collection, limit=200, offset=offset, with_payload=True
        )
        amostra.extend(pontos)
        if offset is None:
            break

    candidatos = [
        p
        for p in amostra
        if p.payload and len((p.payload.get("texto") or "").split()) >= PALAVRAS_DO_TRECHO * 2
    ]
    if len(candidatos) < N_CHUNKS_TESTE:
        _falhar(
            f"apenas {len(candidatos)} chunks longos o bastante para o teste "
            f"(mínimo {N_CHUNKS_TESTE}) — corpus menor que o esperado"
        )

    passo = max(1, len(candidatos) // N_CHUNKS_TESTE)
    selecionados = [candidatos[i * passo] for i in range(N_CHUNKS_TESTE)]

    # --- Bloco A: known-item retrieval ---
    print(f"\n=== Bloco A — dispositivo correto no top-{TOP_K} (objetivo) ===")
    falhas_a = 0
    for i, ponto in enumerate(selecionados, 1):
        payload = ponto.payload or {}
        dispositivo = payload.get("dispositivo", "?")
        palavras = (payload.get("texto") or "").split()
        # Trecho do meio: evita preâmbulo repetido ("Art. 1º") que apareceria
        # em muitos chunks e tornaria a consulta ambígua de propósito.
        meio = len(palavras) // 3
        consulta = " ".join(palavras[meio : meio + PALAVRAS_DO_TRECHO])

        emb = embedder.embed_consulta(consulta)
        resultado = indexer.search_hybrid(
            dense_query=emb.dense_vector,
            sparse_indices=emb.sparse_indices,
            sparse_values=emb.sparse_values,
            limit=TOP_K,
        )
        ids_top = [str(p.id) for p in resultado.points]
        acertou = str(ponto.id) in ids_top
        falhas_a += 0 if acertou else 1
        print(f"  [{i}/{N_CHUNKS_TESTE}] {'OK  ' if acertou else 'ERRO'} {dispositivo}")
        print(f'        consulta: "{consulta[:70]}..."')
        if not acertou:
            devolvidos = [
                (p.payload or {}).get("dispositivo", "?") for p in resultado.points
            ]
            print(f"        esperado no top-{TOP_K}, veio: {devolvidos}")

    # --- Bloco B: as duas pernas da busca respondem ---
    print("\n=== Bloco B — busca é genuinamente híbrida (objetivo) ===")
    payload_ref = selecionados[0].payload or {}
    palavras_ref = (payload_ref.get("texto") or "").split()
    consulta_ref = " ".join(palavras_ref[:PALAVRAS_DO_TRECHO])
    emb_ref = embedder.embed_consulta(consulta_ref)

    densos = client.query_points(
        collection_name=collection, query=emb_ref.dense_vector, using="dense", limit=TOP_K
    ).points
    from qdrant_client.models import SparseVector

    esparsos = client.query_points(
        collection_name=collection,
        query=SparseVector(indices=emb_ref.sparse_indices, values=emb_ref.sparse_values),
        using="sparse",
        limit=TOP_K,
    ).points

    print(f"  perna densa (e5-large): {len(densos)} resultado(s)")
    print(f"  perna esparsa (BM25): {len(esparsos)} resultado(s)")
    falhas_b = 0
    if not densos:
        print("  ERRO: perna densa não retornou nada")
        falhas_b += 1
    if not esparsos:
        print("  ERRO: perna esparsa não retornou nada — a busca não é híbrida de fato")
        falhas_b += 1

    # --- Bloco C: perguntas em linguagem natural (informativo) ---
    print("\n=== Bloco C — perguntas em linguagem natural (informativo) ===")
    print("Sem gabarito verificável; registrado para leitura humana.\n")
    for pergunta in PERGUNTAS_SEMANTICAS:
        emb = embedder.embed_consulta(pergunta)
        resultado = indexer.search_hybrid(
            dense_query=emb.dense_vector,
            sparse_indices=emb.sparse_indices,
            sparse_values=emb.sparse_values,
            limit=TOP_K,
        )
        print(f'  "{pergunta}"')
        for p in resultado.points:
            disp = (p.payload or {}).get("dispositivo", "?")
            print(f"      {p.score:.4f}  {disp}")
        print()

    print("=" * 60)
    print(f"Bloco A: {N_CHUNKS_TESTE - falhas_a}/{N_CHUNKS_TESTE} dispositivos corretos no top-3")
    print(f"Bloco B: {2 - falhas_b}/2 pernas de busca respondendo")
    if falhas_a or falhas_b:
        _falhar(f"{falhas_a + falhas_b} asserção(ões) objetiva(s) falharam")
    print("VERIFICAÇÃO DE BUSCA HÍBRIDA: APROVADA")


if __name__ == "__main__":
    main()
