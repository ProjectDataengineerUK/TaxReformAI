"""Verifica que a reingestão real via Cloud Composer (dags/ingestao_legal_dag.py)
é idempotente — nunca duplica nem perde pontos no Qdrant.

Roda SEMPRE na nuvem (workflow verificar_composer_producao.yml), nunca local —
política do projeto. Chamado duas vezes pelo workflow: uma vez antes de disparar a
DAG (`antes`), gravando as contagens em /tmp; uma vez depois de ela concluir
(`depois`), comparando com o que foi gravado.

O `point_id` de cada Chunk é determinístico (uuid5 de documento_id:dispositivo, ver
ingestion/chunking/chunk_models.py::Chunk.qdrant_point_id), então uma reingestão
correta SOBRESCREVE os pontos existentes, nunca duplica. Contar por `documento_id`
(mesmo padrão de scripts/verificar_busca_hibrida.py) detecta os dois modos de falha:
contagem aumenta = duplicação; contagem diminui = perda silenciosa.
"""

import argparse
import os
import sys

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

DOCUMENTOS = ["LCP_214_2025", "TCU_RES_388_2026"]
ARQUIVO_CONTAGENS = "/tmp/verificar_composer_contagens_antes.txt"


def contar_pontos(client: QdrantClient, collection: str, documento_id: str) -> int:
    filtro = Filter(must=[FieldCondition(key="documento_id", match=MatchValue(value=documento_id))])
    return client.count(collection_name=collection, count_filter=filtro, exact=True).count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("momento", choices=["antes", "depois"])
    args = parser.parse_args()

    client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
    collection = os.environ.get("QDRANT_COLLECTION_NAME", "legislacao_tributaria")

    contagens = {doc: contar_pontos(client, collection, doc) for doc in DOCUMENTOS}
    for doc, total in contagens.items():
        print(f"{args.momento}:{doc}={total}")

    if args.momento == "antes":
        with open(ARQUIVO_CONTAGENS, "w") as f:
            for doc, total in contagens.items():
                f.write(f"{doc}={total}\n")
        return

    if not os.path.exists(ARQUIVO_CONTAGENS):
        print("FALHA: contagens de 'antes' não encontradas — rode 'antes' primeiro nesta mesma run.")
        sys.exit(1)

    antes: dict[str, int] = {}
    with open(ARQUIVO_CONTAGENS) as f:
        for linha in f:
            doc, total = linha.strip().split("=")
            antes[doc] = int(total)

    divergiu = False
    for doc, total in contagens.items():
        if total != antes.get(doc):
            print(
                f"FALHA: {doc} tinha {antes.get(doc)} pontos antes, {total} depois — "
                "reingestão NÃO é idempotente (duplicação ou perda)."
            )
            divergiu = True
    if divergiu:
        sys.exit(1)
    print("OK idempotência confirmada — contagens idênticas antes/depois.")


if __name__ == "__main__":
    main()
