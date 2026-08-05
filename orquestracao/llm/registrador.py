"""Registra cada chamada real ao LLM — best-effort, nunca propaga exceção
(Decision 4 do DESIGN_PAINEL_OBSERVABILIDADE.md), mesma disciplina de
`api/audit.py::registrar_com_seguranca`. Sem isto, `uso_llm` nunca teria
uma linha e a aba de custo do painel de observabilidade ficaria sempre
vazia — mas uma falha ao gravar não pode, em hipótese nenhuma, derrubar
`/v1/tax/query` (AT-004 do DEFINE)."""

import logging
from typing import Protocol

logger = logging.getLogger("orquestracao.llm.registrador")


class RegistradorUsoLLM(Protocol):
    def registrar(
        self,
        no_origem: str,
        modelo: str,
        tokens_entrada: int,
        tokens_saida: int,
        sucesso: bool,
        erro_detalhe: str | None = None,
    ) -> None: ...


class RegistradorUsoLLMPostgres:
    """Real — grava em `uso_llm` via o mesmo pool de conexão já injetado pela
    API (`api/db.py::get_db_pool`). `pool` pode ser `None` (mesmo estado de
    ambiente sem `DB_INSTANCE_CONNECTION_NAME`) — nesse caso não faz nada,
    igual ao audit log."""

    def __init__(self, pool):
        self._pool = pool

    def registrar(
        self,
        no_origem: str,
        modelo: str,
        tokens_entrada: int,
        tokens_saida: int,
        sucesso: bool,
        erro_detalhe: str | None = None,
    ) -> None:
        if self._pool is None:
            return
        try:
            with self._pool.connection() as conexao, conexao.cursor() as cur:
                cur.execute(
                    "INSERT INTO uso_llm "
                    "(no_origem, modelo, tokens_entrada, tokens_saida, sucesso, erro_detalhe) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (no_origem, modelo, tokens_entrada, tokens_saida, sucesso, erro_detalhe),
                )
        except Exception:  # nunca propaga, mesma disciplina de registrar_com_seguranca
            logger.exception(
                "Falha ao registrar uso de LLM (no_origem=%s) — chamada ao LLM segue normalmente",
                no_origem,
            )


class RegistradorUsoLLMNulo:
    """No-op explícito — usado em `tests/` e em qualquer contexto sem Cloud
    SQL, para nunca precisar de `if self._registrador:` espalhado pelo
    cliente. Sem estado próprio, seguro para reusar como singleton."""

    def registrar(
        self,
        no_origem: str,
        modelo: str,
        tokens_entrada: int,
        tokens_saida: int,
        sucesso: bool,
        erro_detalhe: str | None = None,
    ) -> None:
        return


REGISTRADOR_NULO = RegistradorUsoLLMNulo()
