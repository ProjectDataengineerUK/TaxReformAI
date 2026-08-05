"""RegistradorUsoLLM nunca pode propagar exceção — AT-004 do
DEFINE_PAINEL_OBSERVABILIDADE.md: uma falha ao gravar uso de LLM não pode
derrubar /v1/tax/query. Mesma disciplina de tests/test_audit.py, mas para
`orquestracao/llm/registrador.py`."""

from contextlib import contextmanager

from orquestracao.llm.registrador import (
    RegistradorUsoLLMNulo,
    RegistradorUsoLLMPostgres,
)


class FakeCursor:
    def __init__(self, espiao):
        self._espiao = espiao

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        self._espiao.append((sql, params))


class FakeConexao:
    def __init__(self, espiao):
        self._espiao = espiao

    def cursor(self):
        return FakeCursor(self._espiao)


class FakePool:
    def __init__(self, falhar: bool = False):
        self.falhar = falhar
        self.queries: list[tuple] = []

    @contextmanager
    def connection(self):
        if self.falhar:
            raise ConnectionError("Cloud SQL indisponível (simulado)")
        yield FakeConexao(self.queries)


def test_pool_none_e_no_op_silencioso():
    registrador = RegistradorUsoLLMPostgres(None)
    registrador.registrar("classificador", "claude-haiku-4-5", 10, 5, sucesso=True)


def test_grava_chamada_com_sucesso():
    pool = FakePool()
    registrador = RegistradorUsoLLMPostgres(pool)

    registrador.registrar("sintetizador", "claude-sonnet-5", 500, 200, sucesso=True)

    assert len(pool.queries) == 1
    sql, params = pool.queries[0]
    assert "INSERT INTO uso_llm" in sql
    assert params == ("sintetizador", "claude-sonnet-5", 500, 200, True, None)


def test_grava_chamada_com_falha_incluindo_erro_detalhe():
    pool = FakePool()
    registrador = RegistradorUsoLLMPostgres(pool)

    registrador.registrar(
        "extrator_regras", "claude-sonnet-5", 0, 0, sucesso=False, erro_detalhe="timeout"
    )

    _, params = pool.queries[0]
    assert params == ("extrator_regras", "claude-sonnet-5", 0, 0, False, "timeout")


def test_conexao_indisponivel_nao_propaga():
    """O caso mais importante (AT-004): Cloud SQL fora do ar durante o
    registro de uso não pode derrubar a chamada real ao LLM."""
    registrador = RegistradorUsoLLMPostgres(FakePool(falhar=True))

    registrador.registrar("classificador", "claude-haiku-4-5", 10, 5, sucesso=True)


def test_erro_dentro_do_cursor_tambem_nao_propaga():
    class CursorQueQuebra:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, *_args, **_kwargs):
            raise RuntimeError("erro de integridade simulado")

    class ConexaoComCursorQuebrado:
        def cursor(self):
            return CursorQueQuebra()

    class PoolComConexaoQuebrada:
        @contextmanager
        def connection(self):
            yield ConexaoComCursorQuebrado()

    registrador = RegistradorUsoLLMPostgres(PoolComConexaoQuebrada())

    registrador.registrar("sintetizador", "claude-sonnet-5", 1, 1, sucesso=True)


def test_registrador_nulo_nunca_faz_nada():
    RegistradorUsoLLMNulo().registrar("classificador", "claude-haiku-4-5", 10, 5, sucesso=True)
