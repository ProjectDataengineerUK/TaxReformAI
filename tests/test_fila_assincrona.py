"""Testes unitários de FILA_ASSINCRONA_CELERY_REDIS — verificação do token
OIDC e a lógica de processamento de linhas, sem Cloud Tasks/GCS/Postgres
reais (esses só via workflow_dispatch, mesma disciplina de todo script de
infraestrutura real deste projeto)."""

from uuid import uuid4

import pytest

pytest.importorskip("google.auth", reason="google-auth não instalado")

from api.empresa_skus import ResultadoProcessamentoUpload, processar_linhas_upload
from api.tasks_cloud import verificar_token_oidc


class TestVerificarTokenOidc:
    def test_sem_cabecalho_e_invalido(self):
        assert verificar_token_oidc(None) is False

    def test_cabecalho_sem_bearer_e_invalido(self):
        assert verificar_token_oidc("token-cru-sem-prefixo") is False

    def test_token_valido_com_email_certo(self, monkeypatch):
        monkeypatch.setenv("GCP_PROJECT_ID", "projeto-teste")
        monkeypatch.setenv("RUNTIME_SA_EMAIL", "runtime@projeto-teste.iam.gserviceaccount.com")
        monkeypatch.setenv("API_BASE_URL", "https://api.exemplo.com")

        import api.tasks_cloud as tasks_cloud

        monkeypatch.setattr(
            tasks_cloud.id_token,
            "verify_oauth2_token",
            lambda *a, **k: {"email": "runtime@projeto-teste.iam.gserviceaccount.com", "email_verified": True},
        )

        assert verificar_token_oidc("Bearer um-jwt-qualquer") is True

    def test_token_valido_mas_email_errado_e_invalido(self, monkeypatch):
        monkeypatch.setenv("GCP_PROJECT_ID", "projeto-teste")
        monkeypatch.setenv("RUNTIME_SA_EMAIL", "runtime@projeto-teste.iam.gserviceaccount.com")
        monkeypatch.setenv("API_BASE_URL", "https://api.exemplo.com")

        import api.tasks_cloud as tasks_cloud

        monkeypatch.setattr(
            tasks_cloud.id_token,
            "verify_oauth2_token",
            lambda *a, **k: {"email": "outra-sa@outro-projeto.iam.gserviceaccount.com", "email_verified": True},
        )

        assert verificar_token_oidc("Bearer um-jwt-de-outra-sa") is False

    def test_token_invalido_levanta_value_error_vira_false(self, monkeypatch):
        monkeypatch.setenv("GCP_PROJECT_ID", "projeto-teste")
        monkeypatch.setenv("RUNTIME_SA_EMAIL", "runtime@projeto-teste.iam.gserviceaccount.com")
        monkeypatch.setenv("API_BASE_URL", "https://api.exemplo.com")

        import api.tasks_cloud as tasks_cloud

        def _levanta(*_a, **_k):
            raise ValueError("assinatura inválida")

        monkeypatch.setattr(tasks_cloud.id_token, "verify_oauth2_token", _levanta)

        assert verificar_token_oidc("Bearer token-forjado") is False


class TestProcessarLinhasUpload:
    def test_agrega_criados_atualizados_erros(self, monkeypatch):
        import db.repositorio as repositorio

        respostas = iter(
            [
                (object(), True),  # criado
                (object(), False),  # atualizado
            ]
        )
        monkeypatch.setattr(repositorio, "upsert_sku", lambda *a, **k: next(respostas))

        linhas = [
            {"codigo_sku": "SKU-1", "descricao": "Produto 1", "natureza": "MERCADORIA", "ncm_code": "22030000"},
            {"codigo_sku": "SKU-2", "descricao": "Produto 2", "natureza": "MERCADORIA", "ncm_code": "22030000"},
            {"codigo_sku": "", "descricao": "", "natureza": "MERCADORIA"},  # linha inválida
        ]

        resultado = processar_linhas_upload(conexao=object(), tenant_id=uuid4(), linhas=linhas)

        assert isinstance(resultado, ResultadoProcessamentoUpload)
        assert resultado.total_linhas == 3
        assert resultado.criados == 1
        assert resultado.atualizados == 1
        assert resultado.erros == 1
        assert resultado.resultados[0]["situacao"] == "CRIADO"
        assert resultado.resultados[1]["situacao"] == "ATUALIZADO"
        assert resultado.resultados[2]["situacao"] == "ERRO"

    def test_to_dict_e_json_serializavel(self):
        resultado = ResultadoProcessamentoUpload(
            total_linhas=1, criados=1, atualizados=0, erros=0,
            resultados=[{"numero_linha": 1, "codigo_sku": "SKU-1", "situacao": "CRIADO", "motivo": None}],
        )
        d = resultado.to_dict()
        assert d["total_linhas"] == 1
        assert d["resultados"][0]["codigo_sku"] == "SKU-1"
