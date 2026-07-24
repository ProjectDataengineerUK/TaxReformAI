# DAG do Airflow/Cloud Composer que substitui `ingestion/pipeline.py` (CLI
# manual) como orquestrador oficial (blueprint contexto.md, seção 4.2/5.2).
#
# ⚠ `apache-airflow` não instala neste sandbox (`externally-managed-environment`,
# mesmo bloqueio de `qdrant-client`/`fastembed`/`langgraph`) — confirmado via
# `pip3 install --dry-run apache-airflow`. Diferente de `orquestracao/grafo.py`
# (que usa lazy-import para ficar testável sem `langgraph`), este arquivo
# importa `airflow.decorators` no topo do módulo de propósito: o scheduler do
# Airflow descobre DAGs varrendo `dags/` e importando cada arquivo no nível do
# módulo — `@dag`/`@task` só aparecem na UI/scheduler se estiverem decorando
# funções top-level. Um lazy-import produziria uma DAG que nunca seria
# descoberta por um Cloud Composer real, invalidando o propósito da feature.
#
# Consequência aceita (Decision 4, DESIGN_INGESTAO_TCU_E_ETL_AIRFLOW.md): este
# arquivo falha ao importar neste sandbox e fica fora da cobertura de
# `pytest` — validado só por revisão de código até existir um Cloud Composer
# real. A lógica de negócio de cada `@task` é só uma chamada fina a
# `executar_pipeline()` (ingestion/pipeline.py), já testada isoladamente.

from datetime import UTC, datetime

from airflow.decorators import dag, task


@dag(
    dag_id="ingestao_legal_taxreformai",
    schedule="@weekly",
    start_date=datetime(2026, 1, 1, tzinfo=UTC),
    catchup=False,
    tags=["taxreformai", "ingestion"],
)
def ingestao_legal_dag():
    @task()
    def ingest_planalto() -> dict:
        import datetime as dt

        from ingestion.config import Settings
        from ingestion.embedding.hybrid_embedder import FastEmbedHybridEmbedder
        from ingestion.indexing.qdrant_indexer import QdrantIndexer
        from ingestion.pipeline import executar_pipeline
        from ingestion.scraper.planalto_scraper import PlanaltoScraper
        from ingestion.storage.raw_storage import GCSRawStorage

        settings = Settings.from_env()
        storage = GCSRawStorage(settings.gcs_bucket_name, settings.gcp_project_id)
        scraper = PlanaltoScraper(
            storage,
            timeout_seconds=settings.request_timeout_seconds,
            max_retries=settings.max_retries,
        )
        embedder = FastEmbedHybridEmbedder(dense_model_name=settings.dense_embedding_model)
        indexer = QdrantIndexer(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            collection_name=settings.qdrant_collection_name,
        )

        return executar_pipeline(
            url="https://www.planalto.gov.br/ccivil_03/leis/lcp/Lcp214.htm",
            documento_id="LCP_214_2025",
            titulo="Lei Complementar 214/2025",
            esfera="FEDERAL_CBS_IBS",
            data_vigencia_inicio=dt.date(2026, 1, 1),
            scraper=scraper,
            embedder=embedder,
            indexer=indexer,
        )

    @task()
    def ingest_tcu() -> dict:
        import datetime as dt

        from ingestion.config import Settings
        from ingestion.embedding.hybrid_embedder import FastEmbedHybridEmbedder
        from ingestion.indexing.qdrant_indexer import QdrantIndexer
        from ingestion.parser.resolucao_parser import parse_resolucao
        from ingestion.pipeline import executar_pipeline
        from ingestion.scraper.tcu_scraper import TCUScraper
        from ingestion.storage.raw_storage import GCSRawStorage

        settings = Settings.from_env()
        storage = GCSRawStorage(settings.gcs_bucket_name, settings.gcp_project_id)
        scraper = TCUScraper(
            storage,
            timeout_seconds=settings.request_timeout_seconds,
            max_retries=settings.max_retries,
        )
        embedder = FastEmbedHybridEmbedder(dense_model_name=settings.dense_embedding_model)
        indexer = QdrantIndexer(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            collection_name=settings.qdrant_collection_name,
        )

        return executar_pipeline(
            url="https://rotadajurisprudencia.com.br/wp-content/uploads/2026/06/Resolucao-TCU-388_2026.pdf",
            documento_id="TCU_RES_388_2026",
            titulo="Resolução TCU 388/2026",
            esfera="FEDERAL_CBS_IBS_METODOLOGIA",
            data_vigencia_inicio=dt.date(2026, 6, 10),
            scraper=scraper,
            embedder=embedder,
            indexer=indexer,
            parser=parse_resolucao,
        )

    # Planalto e TCU são fontes independentes — sem dependência entre as
    # tasks, o Airflow as executa em paralelo automaticamente.
    ingest_planalto()
    ingest_tcu()


ingestao_legal_dag()
