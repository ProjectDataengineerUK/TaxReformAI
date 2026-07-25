"""Prova que o RLS isola tenants no Cloud SQL real — não apenas infere do
diagnóstico de atributos. Cria dois tenants de teste, grava um parecer para
cada, confirma isolamento, e limpa tudo ao final. Roda só via
migrar_banco.yml, workflow_dispatch com verificar=sim."""

import os
import sys
import uuid

import psycopg

from db.repositorio import ParecerAuditado, registrar_parecer, sessao_do_tenant


def main() -> None:
    conexao = psycopg.connect(os.environ["DATABASE_URL"])
    slug_a = f"_verificacao_a_{uuid.uuid4().hex[:8]}"
    slug_b = f"_verificacao_b_{uuid.uuid4().hex[:8]}"
    tenant_a = tenant_b = None

    try:
        with conexao.cursor() as cur:
            cur.execute(
                "INSERT INTO tenants (slug, nome) VALUES (%s, 'verificação A') RETURNING id",
                (slug_a,),
            )
            tenant_a = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO tenants (slug, nome) VALUES (%s, 'verificação B') RETURNING id",
                (slug_b,),
            )
            tenant_b = cur.fetchone()[0]
        conexao.commit()

        for tenant, texto in ((tenant_a, "prompt de A"), (tenant_b, "prompt de B")):
            registrar_parecer(
                conexao,
                ParecerAuditado(
                    tenant_id=tenant,
                    prompt_consulta=texto,
                    resposta_parecer_md="x",
                    contexto_recuperado_ids=[],
                    payload_calculo={},
                ),
            )

        with sessao_do_tenant(conexao, tenant_a) as cur:
            cur.execute("SELECT prompt_consulta FROM pareceres_audit_log")
            visiveis = [linha[0] for linha in cur.fetchall()]

        if visiveis != ["prompt de A"]:
            print(f"FALHA: RLS não isolou — tenant A viu {visiveis}", file=sys.stderr)
            sys.exit(1)

        with conexao.cursor() as cur:
            cur.execute("SELECT count(*) FROM pareceres_audit_log")
            total_sem_tenant = cur.fetchone()[0]
        conexao.commit()

        if total_sem_tenant != 0:
            print(
                f"FALHA: sem tenant declarado, {total_sem_tenant} linhas visíveis "
                "(esperado 0)",
                file=sys.stderr,
            )
            sys.exit(1)

        print("RLS VERIFICADO CONTRA O CLOUD SQL REAL: isolamento entre tenants confirmado.")
    finally:
        # Só apaga `tenants` — pareceres_audit_log.tenant_id é ON DELETE
        # CASCADE (migração 001), então a cascata cuida do resto. Um DELETE
        # explícito na tabela de audit log aqui seria inútil: ela tem FORCE
        # ROW LEVEL SECURITY e esta sessão não declarou app.tenant_id, então
        # a policy filtraria para zero linhas e o DELETE não apagaria nada.
        with conexao.cursor() as cur:
            cur.execute("DELETE FROM tenants WHERE slug IN (%s, %s)", (slug_a, slug_b))
        conexao.commit()
        conexao.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — borda de CLI, qualquer falha vira exit 1 com mensagem
        print(f"FALHA: {exc}", file=sys.stderr)
        sys.exit(1)
