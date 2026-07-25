"""`registrar_com_seguranca` nunca pode propagar exceção: uma falha ao gravar
audit log não pode derrubar a resposta de um cálculo tributário correto.
Estes testes usam fakes, não Postgres real — o que está sob teste é a
degradação graciosa, não o SQL (isso é `tests/test_schema_postgres.py`)."""

from contextlib import contextmanager
from uuid import uuid4

from api.audit import registrar_com_seguranca

TENANT_UUID = uuid4()


class FakePool:
    def __init__(self, falhar: bool = False):
        self.falhar = falhar
        self.conexoes_abertas = 0

    @contextmanager
    def connection(self):
        if self.falhar:
            raise ConnectionError("Cloud SQL indisponível (simulado)")
        self.conexoes_abertas += 1
        yield object()


def test_pool_none_e_no_op_silencioso():
    """Sem DB_INSTANCE_CONNECTION_NAME no ambiente — o estado de todo teste e
    de qualquer deploy antes do Cloud SQL existir. Não é erro."""
    registrar_com_seguranca(
        None,
        "algum-tenant",
        prompt_consulta="x",
        resposta_parecer_md="y",
        payload_calculo={},
    )


def test_tenant_nao_cadastrado_nao_propaga_e_nao_grava(monkeypatch):
    import db.repositorio as repositorio

    chamadas = []
    monkeypatch.setattr(repositorio, "resolver_tenant", lambda conn, ident: None)
    monkeypatch.setattr(
        repositorio, "registrar_parecer", lambda conn, p: chamadas.append(p)
    )

    registrar_com_seguranca(
        FakePool(),
        "tenant-inexistente",
        prompt_consulta="x",
        resposta_parecer_md="y",
        payload_calculo={},
    )

    assert chamadas == []


def test_tenant_resolvido_grava_com_os_dados_corretos(monkeypatch):
    import db.repositorio as repositorio

    chamadas = []
    monkeypatch.setattr(repositorio, "resolver_tenant", lambda conn, ident: TENANT_UUID)
    monkeypatch.setattr(
        repositorio, "registrar_parecer", lambda conn, p: chamadas.append(p)
    )

    registrar_com_seguranca(
        FakePool(),
        "taxreformai-dev",
        prompt_consulta="quanto de CBS?",
        resposta_parecer_md="**9%**",
        payload_calculo={"ano": 2026},
        contexto_recuperado_ids=["chunk-1"],
    )

    assert len(chamadas) == 1
    parecer = chamadas[0]
    assert parecer.tenant_id == TENANT_UUID
    assert parecer.prompt_consulta == "quanto de CBS?"
    assert parecer.resposta_parecer_md == "**9%**"
    assert parecer.payload_calculo == {"ano": 2026}
    assert parecer.contexto_recuperado_ids == ["chunk-1"]


def test_contexto_recuperado_ids_default_e_lista_vazia(monkeypatch):
    """Sem contexto explícito, grava [] e não None — contexto_recuperado_ids
    é NOT NULL DEFAULT '[]'::jsonb no schema."""
    import db.repositorio as repositorio

    chamadas = []
    monkeypatch.setattr(repositorio, "resolver_tenant", lambda conn, ident: TENANT_UUID)
    monkeypatch.setattr(
        repositorio, "registrar_parecer", lambda conn, p: chamadas.append(p)
    )

    registrar_com_seguranca(
        FakePool(), "t", prompt_consulta="x", resposta_parecer_md="y", payload_calculo={}
    )

    assert chamadas[0].contexto_recuperado_ids == []


def test_conexao_indisponivel_nao_propaga():
    """O caso mais importante: Cloud SQL fora do ar não pode derrubar
    /simulate nem /query — a exceção é capturada e só logada."""
    registrar_com_seguranca(
        FakePool(falhar=True),
        "t",
        prompt_consulta="x",
        resposta_parecer_md="y",
        payload_calculo={},
    )


def test_erro_dentro_de_registrar_parecer_tambem_nao_propaga(monkeypatch):
    import db.repositorio as repositorio

    monkeypatch.setattr(repositorio, "resolver_tenant", lambda conn, ident: TENANT_UUID)

    def _explode(conn, parecer):
        raise RuntimeError("erro de integridade simulado")

    monkeypatch.setattr(repositorio, "registrar_parecer", _explode)

    registrar_com_seguranca(
        FakePool(), "t", prompt_consulta="x", resposta_parecer_md="y", payload_calculo={}
    )
