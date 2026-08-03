from api.empresa_skus import (
    ConsultaSkus,
    SituacaoResolucaoSku,
    consultar_skus_com_seguranca,
    parsear_linha_csv,
    resolver_ncm_nbs_do_item,
    validar_exclusividade,
)


class TestValidarExclusividade:
    def test_mercadoria_valida(self):
        assert validar_exclusividade("MERCADORIA", "22030000", None) is None

    def test_servico_valido(self):
        assert validar_exclusividade("SERVICO", None, "122010000") is None

    def test_mercadoria_sem_ncm_invalida(self):
        assert validar_exclusividade("MERCADORIA", None, None) is not None

    def test_mercadoria_com_nbs_invalida(self):
        assert validar_exclusividade("MERCADORIA", "22030000", "122010000") is not None

    def test_servico_sem_nbs_invalida(self):
        assert validar_exclusividade("SERVICO", None, None) is not None

    def test_servico_com_ncm_invalida(self):
        assert validar_exclusividade("SERVICO", "22030000", "122010000") is not None


class TestParsearLinhaCsv:
    def test_linha_mercadoria_valida(self):
        r = parsear_linha_csv(
            1, {"codigo_sku": "SKU-1", "descricao": "Produto", "natureza": "MERCADORIA", "ncm_code": "2203.00.00"}
        )
        assert r.erro is None
        assert r.ncm_code == "22030000"
        assert r.nbs_code is None

    def test_linha_servico_valida(self):
        r = parsear_linha_csv(
            1, {"codigo_sku": "SKU-2", "descricao": "Serviço", "natureza": "SERVICO", "nbs_code": "1.2201.00.00"}
        )
        assert r.erro is None
        assert r.nbs_code == "122010000"

    def test_codigo_sku_ausente(self):
        r = parsear_linha_csv(1, {"descricao": "x", "natureza": "MERCADORIA", "ncm_code": "22030000"})
        assert r.erro is not None

    def test_descricao_ausente(self):
        r = parsear_linha_csv(1, {"codigo_sku": "SKU-1", "natureza": "MERCADORIA", "ncm_code": "22030000"})
        assert r.erro is not None

    def test_natureza_invalida(self):
        r = parsear_linha_csv(1, {"codigo_sku": "SKU-1", "descricao": "x", "natureza": "OUTRA"})
        assert r.erro is not None

    def test_ncm_malformado(self):
        r = parsear_linha_csv(
            1, {"codigo_sku": "SKU-1", "descricao": "x", "natureza": "MERCADORIA", "ncm_code": "abc"}
        )
        assert r.erro is not None

    def test_nbs_malformado(self):
        r = parsear_linha_csv(
            1, {"codigo_sku": "SKU-1", "descricao": "x", "natureza": "SERVICO", "nbs_code": "123"}
        )
        assert r.erro is not None

    def test_exclusividade_violada_na_linha(self):
        r = parsear_linha_csv(
            1,
            {
                "codigo_sku": "SKU-1", "descricao": "x", "natureza": "MERCADORIA",
                "ncm_code": "22030000", "nbs_code": "122010000",
            },
        )
        assert r.erro is not None


class TestResolverNcmNbsDoItem:
    def test_ncm_explicito_vence(self):
        r = resolver_ncm_nbs_do_item("MERCADORIA", "22030000", None, "SKU-1", ConsultaSkus(disponivel=True))
        assert r.situacao is SituacaoResolucaoSku.NAO_NECESSARIO
        assert r.ncm_efetivo == "22030000"

    def test_nbs_explicito_vence(self):
        r = resolver_ncm_nbs_do_item("SERVICO", None, "122010000", "SKU-1", ConsultaSkus(disponivel=True))
        assert r.situacao is SituacaoResolucaoSku.NAO_NECESSARIO
        assert r.nbs_efetivo == "122010000"

    def test_consulta_indisponivel(self):
        r = resolver_ncm_nbs_do_item("MERCADORIA", None, None, "SKU-1", ConsultaSkus(disponivel=False))
        assert r.situacao is SituacaoResolucaoSku.CONSULTA_INDISPONIVEL

    def test_sku_nao_cadastrado(self):
        r = resolver_ncm_nbs_do_item("MERCADORIA", None, None, "SKU-1", ConsultaSkus(disponivel=True, por_codigo={}))
        assert r.situacao is SituacaoResolucaoSku.NAO_CADASTRADO

    def test_resolve_do_catalogo_mercadoria(self):
        class _Registro:
            ncm_code = "22030000"
            nbs_code = None

        consulta = ConsultaSkus(disponivel=True, por_codigo={"SKU-1": _Registro()})
        r = resolver_ncm_nbs_do_item("MERCADORIA", None, None, "SKU-1", consulta)
        assert r.situacao is SituacaoResolucaoSku.RESOLVIDO_CATALOGO
        assert r.ncm_efetivo == "22030000"

    def test_resolve_do_catalogo_servico(self):
        class _Registro:
            ncm_code = None
            nbs_code = "122010000"

        consulta = ConsultaSkus(disponivel=True, por_codigo={"SKU-2": _Registro()})
        r = resolver_ncm_nbs_do_item("SERVICO", None, None, "SKU-2", consulta)
        assert r.situacao is SituacaoResolucaoSku.RESOLVIDO_CATALOGO
        assert r.nbs_efetivo == "122010000"


class TestConsultarSkusComSeguranca:
    def test_pool_none_e_indisponivel(self):
        assert consultar_skus_com_seguranca(None, "tenant-x", ["SKU-1"]).disponivel is False

    def test_lista_vazia_e_disponivel(self):
        assert consultar_skus_com_seguranca(object(), "tenant-x", []).disponivel is True
