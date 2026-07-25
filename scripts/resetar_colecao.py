"""Apaga a coleção do Qdrant antes de uma reingestão limpa.

Usado pelo ingestao.yml quando `recriar_colecao=sim`. Roda só na nuvem.
"""

import os

from ingestion.indexing.qdrant_indexer import QdrantIndexer

indexer = QdrantIndexer(
    url=os.environ["QDRANT_URL"],
    api_key=os.environ["QDRANT_API_KEY"],
    collection_name=os.environ.get("QDRANT_COLLECTION_NAME", "legislacao_tributaria"),
)
existia = indexer.drop_collection()
print("coleção apagada" if existia else "coleção não existia — nada a fazer")
