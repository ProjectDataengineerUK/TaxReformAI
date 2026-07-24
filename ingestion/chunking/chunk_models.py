import uuid
from datetime import date

from pydantic import BaseModel

# Namespace fixo para os point ids do Qdrant. Não pode mudar: o id é a chave de
# idempotência da reingestão (mesmo dispositivo → mesmo ponto, sobrescrito em vez
# de duplicado). Trocar o namespace duplicaria o corpus inteiro na coleção.
_NAMESPACE_CHUNK = uuid.UUID("6f0a1c3e-7b2d-4e51-9a8f-2c4d6e8b0a13")


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
        """Id determinístico do ponto no Qdrant.

        Precisa ser UUID (ou inteiro sem sinal) — o Qdrant rejeita qualquer outra
        string com 400. Um hexdigest de sha256 parece um id válido, mas não é.
        """
        return str(uuid.uuid5(_NAMESPACE_CHUNK, f"{self.documento_id}:{self.dispositivo}"))
