from datetime import date

from pydantic import BaseModel


class Chunk(BaseModel):
    documento_id: str
    dispositivo: str  # ex: "Art. 18, §2º, Inciso II"
    esfera: str  # ex: "SUBNACIONAL_IBS"
    data_vigencia_inicio: date
    data_vigencia_fim: date | None = None
    ncm_relacionadas: list[str] = []
    regime: str | None = None
    texto: str  # conteúdo do chunk (child, com contexto do parent)
    parent_texto: str | None = None  # texto completo do Artigo (contexto herdado)
    fonte_url: str  # URL de origem, para lineage/auditabilidade

    def qdrant_point_id(self) -> str:
        import hashlib

        return hashlib.sha256(f"{self.documento_id}:{self.dispositivo}".encode()).hexdigest()
