"""Aplicador de migrações em SQL puro.

Sem ORM nem Alembic: o projeto não tem ORM em lugar nenhum e usa `Protocol` +
implementação real/fake em todas as camadas. Introduzir SQLAlchemy por uma
feature criaria um segundo estilo de acesso a dados no mesmo repositório.

Para um schema deste tamanho, arquivos `NNN_*.sql` aplicados em ordem e
registrados numa tabela de controle bastam — e não escondem o SQL de quem
precisa auditá-lo, que é metade do ponto num sistema de compliance fiscal.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DIRETORIO_MIGRACOES = Path(__file__).parent / "migrations"

SQL_TABELA_CONTROLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    versao      TEXT PRIMARY KEY,
    aplicada_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


@dataclass(frozen=True)
class Migracao:
    versao: str
    caminho: Path

    @property
    def sql(self) -> str:
        return self.caminho.read_text(encoding="utf-8")


def listar_migracoes(diretorio: Path = DIRETORIO_MIGRACOES) -> list[Migracao]:
    """Ordena pelo prefixo numérico do nome, não pela ordem do sistema de
    arquivos — `glob` não garante ordem, e aplicar 002 antes de 001 quebraria
    de um jeito que só apareceria em outra máquina."""
    arquivos = sorted(diretorio.glob("*.sql"), key=lambda p: p.name)
    return [Migracao(versao=p.name, caminho=p) for p in arquivos]


def aplicar_migracoes(conexao, diretorio: Path = DIRETORIO_MIGRACOES) -> list[str]:
    """Aplica as migrações ainda não registradas. Devolve as que rodaram.

    Idempotente: chamar duas vezes não reaplica nem falha. Cada migração roda
    na sua própria transação, junto com o registro em `schema_migrations` — se
    o SQL falhar no meio, nada daquela migração fica aplicado e ela não é
    marcada como concluída.
    """
    aplicadas: list[str] = []

    with conexao.cursor() as cur:
        cur.execute(SQL_TABELA_CONTROLE)
        conexao.commit()
        cur.execute("SELECT versao FROM schema_migrations")
        ja_aplicadas = {linha[0] for linha in cur.fetchall()}

    for migracao in listar_migracoes(diretorio):
        if migracao.versao in ja_aplicadas:
            continue
        try:
            with conexao.cursor() as cur:
                cur.execute(migracao.sql)
                cur.execute(
                    "INSERT INTO schema_migrations (versao) VALUES (%s)",
                    (migracao.versao,),
                )
            conexao.commit()
        except Exception:
            conexao.rollback()
            raise
        aplicadas.append(migracao.versao)

    return aplicadas
