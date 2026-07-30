"""Os 4 Anexos de redução a zero contra PostgreSQL real — mesmo padrão de
`test_tipi_db.py`: pula sem `DATABASE_URL`, roda de verdade no CI contra um
container `postgres:16`.

O que só existe aqui, e não nos testes com fake: as CHECK constraints (que são a
garantia real contra erro de transcrição, e vivem no banco, não no Python), o
seed carregado pelas migrações de verdade (005 + 007 + 008), a chave composta
`(anexo, item, sub_item)` com a FK que ela sustenta, e a prova de que a migração
006 derrubou `regras_tributarias_cache`.
"""

from __future__ import annotations

import os

import pytest

from db.repositorio import buscar_reducao_por_prefixo

psycopg = pytest.importorskip("psycopg", reason="psycopg não instalado")

DATABASE_URL = os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="DATABASE_URL ausente — sem PostgreSQL para testar"
)


@pytest.fixture
def conexao():
    from db.migrador import aplicar_migracoes

    con = psycopg.connect(DATABASE_URL)
    aplicar_migracoes(con)
    yield con
    con.rollback()
    con.close()


# Seed — contagens de fechamento do DESIGN -----------------------------------


def test_os_renames_das_migracoes_007_e_009_apagaram_os_nomes_antigos(conexao):
    """`ALTER TABLE ... RENAME` preserva dados, índices e privilégios — mas o
    nome antigo tem de sumir, senão alguém escreveria numa cópia esquecida.
    Duas gerações de nome: `cesta_basica_anexo_i*` (007) e `anexos_reducao_zero*`
    (009), nenhuma pode sobreviver ao lado da atual."""
    with conexao.cursor() as cur:
        cur.execute("SELECT to_regclass('public.cesta_basica_anexo_i')")
        assert cur.fetchone()[0] is None
        cur.execute("SELECT to_regclass('public.cesta_basica_anexo_i_ncm')")
        assert cur.fetchone()[0] is None
        cur.execute("SELECT to_regclass('public.anexos_reducao_zero')")
        assert cur.fetchone()[0] is None
        cur.execute("SELECT to_regclass('public.anexos_reducao_zero_ncm')")
        assert cur.fetchone()[0] is None
        cur.execute("SELECT to_regclass('public.anexos_reducao')")
        assert cur.fetchone()[0] is not None


def test_seed_carregou_os_60_itens_dos_quatro_anexos(conexao):
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT anexo, count(*) FROM anexos_reducao GROUP BY anexo ORDER BY anexo"
        )
        contagens = dict(cur.fetchall())

    assert contagens == {"I": 26, "XII": 20, "XIII": 8, "XV": 6}


def test_seed_carregou_os_151_prefixos_por_anexo(conexao):
    """Contagem é teste de truncamento: uma migração cortada pela metade passa
    em toda constraint e falha aqui. Por Anexo, para que a falha diga onde."""
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT anexo, count(*) FROM anexos_reducao_ncm "
            "GROUP BY anexo ORDER BY anexo"
        )
        contagens = dict(cur.fetchall())

    assert contagens == {"I": 95, "XII": 24, "XIII": 7, "XV": 25}


def test_seed_carregou_127_inclusoes_e_24_excecoes(conexao):
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT excecao, count(*) FROM anexos_reducao_ncm "
            "GROUP BY excecao ORDER BY excecao"
        )
        contagens = dict(cur.fetchall())

    assert contagens == {False: 127, True: 24}


def test_o_ordinal_de_cada_anexo_e_unico_e_numerico(conexao):
    """Numeral romano não ordena lexicograficamente — o ordinal existe para o
    desempate poder ordenar Anexos (Decisão 3)."""
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT anexo, anexo_ordem FROM anexos_reducao ORDER BY anexo_ordem"
        )
        pares = cur.fetchall()

    assert pares == [("I", 1), ("XII", 12), ("XIII", 13), ("XV", 15)]


def test_comprimentos_de_prefixo_presentes_sao_a_lista_da_ncm(conexao):
    """O 2 entrou com o Capítulo 6 (Anexo XV, item 4); o 7 só existe no Anexo I.
    Nenhum 3: a NCM/SH não tem esse nível."""
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT length(prefixo) FROM anexos_reducao_ncm ORDER BY 1"
        )
        comprimentos = [linha[0] for linha in cur.fetchall()]

    assert comprimentos == [2, 4, 5, 6, 7, 8]


def test_o_unico_prefixo_de_dois_digitos_e_o_capitulo_6_do_anexo_xv(conexao):
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT anexo, item, prefixo, texto_ncm FROM anexos_reducao_ncm "
            "WHERE length(prefixo) = 2"
        )
        linhas = cur.fetchall()

    # `texto_ncm` guarda a grafia do CÓDIGO ('06'), não a prosa do DOU
    # ('Capítulo 6') — senão `prefixo_bate_com_texto` derivaria '6'.
    assert linhas == [("XV", 4, "06", "06")]


def test_toda_excecao_desce_de_uma_inclusao_do_mesmo_item(conexao):
    """A mesma consulta que a migração 008 executa como asserção. Uma exceção
    órfã é ou erro de transcrição, ou um "exceto" DESCRITIVO virado linha
    (Decisão 6) — nos dois casos a linha seria inerte."""
    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT e.anexo, e.item, e.sub_item, e.prefixo FROM anexos_reducao_ncm e
            WHERE e.excecao IS TRUE
              AND NOT EXISTS (
                  SELECT 1 FROM anexos_reducao_ncm i
                  WHERE i.anexo = e.anexo AND i.item = e.item AND i.sub_item = e.sub_item
                    AND i.excecao IS FALSE AND e.prefixo LIKE i.prefixo || '%'
              )
            """
        )
        orfas = cur.fetchall()

    assert orfas == []


def test_a_assercao_de_excecao_orfa_de_fato_pega_uma_orfa(conexao):
    """A asserção da migração só vale se ela reprovaria o dado errado. Aqui uma
    exceção que não desce de nenhuma inclusão do próprio item é inserida de
    propósito, e a consulta precisa encontrá-la."""
    with conexao.cursor() as cur:
        cur.execute(
            "INSERT INTO anexos_reducao_ncm (anexo, item, sub_item, prefixo, "
            "excecao, texto_ncm) VALUES ('XII', 6, 0, '90229999', TRUE, '9022.99.99')"
        )
        cur.execute(
            """
            SELECT e.anexo, e.item, e.prefixo FROM anexos_reducao_ncm e
            WHERE e.excecao IS TRUE
              AND NOT EXISTS (
                  SELECT 1 FROM anexos_reducao_ncm i
                  WHERE i.anexo = e.anexo AND i.item = e.item AND i.sub_item = e.sub_item
                    AND i.excecao IS FALSE AND e.prefixo LIKE i.prefixo || '%'
              )
            """
        )
        orfas = cur.fetchall()

    assert orfas == [("XII", 6, "90229999")]
    conexao.rollback()


def test_so_os_dois_cabecalhos_conhecidos_nao_tem_linha_de_prefixo(conexao):
    """XII/1 e XIII/2 são cabeçalhos sem célula de NCM no DOU. Qualquer outro
    item sem prefixo seria INSERT truncado (Decisão 7)."""
    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT i.anexo, i.item, i.sub_item FROM anexos_reducao i
            WHERE NOT EXISTS (
                SELECT 1 FROM anexos_reducao_ncm p
                WHERE p.anexo = i.anexo AND p.item = i.item AND p.sub_item = i.sub_item
            )
            ORDER BY i.anexo_ordem, i.item
            """
        )
        sem_prefixo = cur.fetchall()

    assert sem_prefixo == [("XII", 1, 0), ("XIII", 2, 0)]


def test_todo_sub_item_tem_o_cabecalho_que_lhe_da_sentido(conexao):
    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT f.anexo, f.item, f.sub_item FROM anexos_reducao f
            WHERE f.sub_item > 0 AND NOT EXISTS (
                SELECT 1 FROM anexos_reducao c
                WHERE c.anexo = f.anexo AND c.item = f.item AND c.sub_item = 0
            )
            """
        )
        assert cur.fetchall() == []

        cur.execute("SELECT count(*) FROM anexos_reducao WHERE sub_item > 0")
        assert cur.fetchone()[0] == 5  # XII/1.1-1.3 e XIII/2.1-2.2


def test_nenhum_codigo_concreto_e_compartilhado_entre_anexos_diferentes(conexao):
    """Decisão 12: dois Anexos compartilham um código concreto de 8 dígitos se,
    e somente se, um prefixo de inclusão de um for prefixo do outro — a
    equivalência é exata, então o teste não precisa da tabela da NCM nem inventa
    códigos.

    TESTE, não asserção de migração: sobreposição entre Anexos não é ilegal (a
    lei pode criar uma) e o desempate já a trata deterministicamente. Isto existe
    para tornar o fato VISÍVEL quando mudar. A margem hoje é de UMA posição: o
    Anexo I usa `0713` (feijões) e o Anexo XV lista `07.01`-`07.10` e `07.14`.
    """
    with conexao.cursor() as cur:
        cur.execute(
            """
            SELECT a.anexo, a.prefixo, b.anexo, b.prefixo
            FROM anexos_reducao_ncm a
            JOIN anexos_reducao_ncm b
              ON a.anexo < b.anexo
             AND (b.prefixo LIKE a.prefixo || '%' OR a.prefixo LIKE b.prefixo || '%')
            WHERE a.excecao IS FALSE AND b.excecao IS FALSE
            """
        )
        colisoes = cur.fetchall()

    assert colisoes == []


# CHECK constraints — a garantia mora no banco, não na disciplina do código ---


def test_check_recusa_prefixo_que_nao_bate_com_a_grafia_do_dou(conexao):
    """O erro mais provável desta feature: transcrever `0210.99.1` e digitar
    `02109910` no prefixo. Sem esta CHECK, viraria uma mercadoria a mais com
    alíquota zero, descoberta por um cliente."""
    with pytest.raises(psycopg.errors.CheckViolation):
        with conexao.cursor() as cur:
            cur.execute(
                "INSERT INTO anexos_reducao_ncm (anexo, item, prefixo, texto_ncm) "
                "VALUES ('I', 19, '02109910', '0210.99.1')"
            )
    conexao.rollback()


def test_check_recusa_prefixo_de_tres_digitos_que_a_ncm_nao_tem(conexao):
    """`prefixos_ncm` gera exatamente {2,4,5,6,7,8}: uma linha de 3 nunca casaria
    com nada — falso negativo permanente e mudo. É por isso que a CHECK usa
    LISTA de comprimentos, e não o intervalo 2..8 (Decisão 4)."""
    with pytest.raises(psycopg.errors.CheckViolation):
        with conexao.cursor() as cur:
            cur.execute(
                "INSERT INTO anexos_reducao_ncm (anexo, item, prefixo, texto_ncm) "
                "VALUES ('XV', 4, '060', '060')"
            )
    conexao.rollback()


def test_check_aceita_o_prefixo_de_dois_digitos_que_a_migracao_005_proibia(conexao):
    """O outro lado da mesma mudança: o capítulo (2 dígitos) passou a ser
    aceito. Sem isto o Anexo XV, item 4, seria inserível apenas como erro."""
    with conexao.cursor() as cur:
        cur.execute(
            "INSERT INTO anexos_reducao_ncm (anexo, item, prefixo, texto_ncm) "
            "VALUES ('XV', 5, '07', '07')"
        )
        cur.execute(
            "SELECT count(*) FROM anexos_reducao_ncm WHERE prefixo = '07'"
        )
        assert cur.fetchone()[0] == 1
    conexao.rollback()


def test_check_recusa_anexo_fora_do_conjunto_de_reducao_a_zero(conexao):
    """A tabela declara no nome e nesta CHECK que trata só de redução a ZERO.
    O Anexo IV (60%, art. 131) tem outra forma de cálculo e não entra aqui por
    ser "NCM também" (Decisão 3)."""
    with pytest.raises(psycopg.errors.CheckViolation):
        with conexao.cursor() as cur:
            cur.execute(
                "INSERT INTO anexos_reducao "
                "(anexo, anexo_ordem, item, descricao, dispositivo_legal_ref) "
                "VALUES ('IV', 4, 1, 'inventado', 'LCP 214/2025, Anexo IV, item 1')"
            )
    conexao.rollback()


def test_check_recusa_ordinal_que_discorda_do_rotulo(conexao):
    """O ordinal mora ao lado do rótulo justamente para não poder divergir: com
    um mapa em Python, o dia em que só um for atualizado produz uma ordem de
    desempate silenciosamente errada."""
    with pytest.raises(psycopg.errors.CheckViolation):
        with conexao.cursor() as cur:
            cur.execute(
                "INSERT INTO anexos_reducao "
                "(anexo, anexo_ordem, item, descricao, dispositivo_legal_ref) "
                "VALUES ('XV', 13, 99, 'inventado', "
                "'LCP 214/2025, art. 148, Anexo XV, item 99')"
            )
    conexao.rollback()


def test_check_recusa_citacao_legal_que_nao_bate_com_a_chave(conexao):
    """Transcrever "item 43" numa linha cujo item é 44 é invisível: o número
    certo continua na chave e o cliente recebe a citação errada. A CHECK compara
    as duas grafias no INSERT. (Item inexistente de propósito, para a falha ser
    a da CHECK e não a da chave primária.)"""
    with pytest.raises(psycopg.errors.CheckViolation):
        with conexao.cursor() as cur:
            cur.execute(
                "INSERT INTO anexos_reducao "
                "(anexo, anexo_ordem, item, descricao, dispositivo_legal_ref) "
                "VALUES ('XII', 12, 44, 'inventado', "
                "'LCP 214/2025, art. 144, Anexo XII, item 43')"
            )
    conexao.rollback()


def test_check_recusa_citacao_que_ignora_o_sub_item(conexao):
    """Um sub-item citado como se fosse o item inteiro apontaria o cliente para
    o cabeçalho, não para a linha que de fato lhe deu a redução."""
    with pytest.raises(psycopg.errors.CheckViolation):
        with conexao.cursor() as cur:
            cur.execute(
                "INSERT INTO anexos_reducao "
                "(anexo, anexo_ordem, item, sub_item, descricao, dispositivo_legal_ref) "
                "VALUES ('XIII', 13, 2, 3, 'inventado', "
                "'LCP 214/2025, art. 145, Anexo XIII, item 2')"
            )
    conexao.rollback()


def test_prefixo_duplicado_no_mesmo_item_e_rejeitado(conexao):
    with pytest.raises(psycopg.errors.UniqueViolation):
        with conexao.cursor() as cur:
            cur.execute(
                "INSERT INTO anexos_reducao_ncm "
                "(anexo, item, sub_item, prefixo, excecao, texto_ncm) "
                "VALUES ('XIII', 2, 1, '87131000', FALSE, '8713.10.00')"
            )
    conexao.rollback()


def test_o_mesmo_prefixo_em_sub_itens_diferentes_e_permitido(conexao):
    """`9018.19.80` está nos itens 1.2, 1.3 e 14 do Anexo XII — a UNIQUE é sobre
    a chave inteira, senão o Anexo real não caberia na tabela."""
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT item, sub_item FROM anexos_reducao_ncm "
            "WHERE prefixo = '90181980' ORDER BY item, sub_item"
        )
        assert cur.fetchall() == [(1, 2), (1, 3), (14, 0)]


def test_prefixo_sem_item_existente_e_rejeitado(conexao):
    """A FK é composta `(anexo, item, sub_item)`. Ela só existe de verdade
    porque `sub_item` é NOT NULL: com MATCH SIMPLE, uma coluna NULL satisfaria
    a FK TRIVIALMENTE — integridade referencial desligada sem erro nenhum."""
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with conexao.cursor() as cur:
            cur.execute(
                "INSERT INTO anexos_reducao_ncm "
                "(anexo, item, sub_item, prefixo, texto_ncm) "
                "VALUES ('XIII', 2, 9, '99999999', '9999.99.99')"
            )
    conexao.rollback()


def test_prefixo_apontando_para_o_item_certo_do_anexo_errado_e_rejeitado(conexao):
    """O Anexo entra na FK: o item 5 existe no I e no XII, mas o par
    (XIII, 5, 0) tem item, e (XV, 20, 0) não — antes da chave composta, `item`
    sozinho aceitaria qualquer um."""
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with conexao.cursor() as cur:
            cur.execute(
                "INSERT INTO anexos_reducao_ncm "
                "(anexo, item, sub_item, prefixo, texto_ncm) "
                "VALUES ('XV', 20, 0, '99999999', '9999.99.99')"
            )
    conexao.rollback()


# buscar_reducao_por_prefixo — o lookup que /v1/tax/simulate faz ---------


class CursorEspiao:
    """Conta `execute` sobre a conexão real: "1 query, não N" precisa ser
    verificado contra o driver de verdade, não só contra um fake."""

    def __init__(self, conexao):
        self._conexao = conexao
        self.execucoes = 0

    def cursor(self):
        espiao = self

        class _Cursor:
            def __init__(self):
                self._cur = espiao._conexao.cursor()

            def __enter__(self):
                self._cur.__enter__()
                return self

            def __exit__(self, *args):
                return self._cur.__exit__(*args)

            def execute(self, sql, params=None):
                espiao.execucoes += 1
                return self._cur.execute(sql, params)

            def fetchall(self):
                return self._cur.fetchall()

        return _Cursor()


def test_lookup_devolve_inclusao_e_excecao_no_mesmo_lote(conexao):
    """Uma exceção só importa quando ela própria é prefixo do código, então cai
    no mesmo `= ANY` — sem segunda consulta."""
    from api.ncm import prefixos_ncm

    linhas = buscar_reducao_por_prefixo(conexao, prefixos_ncm("90213991"))

    por_prefixo = {linha.prefixo: linha for linha in linhas}
    assert por_prefixo["90213"].excecao is False
    assert (por_prefixo["90213"].anexo, por_prefixo["90213"].item) == ("XII", 5)
    assert por_prefixo["90213991"].excecao is True
    assert por_prefixo["90213991"].texto_ncm == "9021.39.91"


def test_lookup_traz_descricao_e_dispositivo_do_item_pelo_join(conexao):
    linhas = buscar_reducao_por_prefixo(conexao, ["04051000"])

    assert len(linhas) == 1
    assert (linhas[0].anexo, linhas[0].item, linhas[0].sub_item) == ("I", 5, 0)
    assert linhas[0].dispositivo_legal_ref == "LCP 214/2025, art. 125, Anexo I, item 5"
    assert linhas[0].descricao.startswith("Manteiga")
    assert linhas[0].alinea is None
    assert linhas[0].descricao_contexto is None


def test_lookup_traz_a_descricao_do_pai_para_o_sub_item(conexao):
    """O LEFT JOIN da Decisão 7: sem ele, a resposta citaria "Sem mecanismo de
    propulsão" como fundamentação legal de uma cadeira de rodas."""
    linhas = buscar_reducao_por_prefixo(conexao, ["87131000"])

    assert len(linhas) == 1
    assert (linhas[0].anexo, linhas[0].item, linhas[0].sub_item) == ("XIII", 2, 1)
    assert linhas[0].descricao == "Sem mecanismo de propulsão"
    assert linhas[0].descricao_contexto.startswith("CADEIRA DE RODAS")


def test_lookup_nunca_devolve_um_cabecalho(conexao):
    """Cabeçalhos (XII/1 e XIII/2) não têm linha de prefixo, então não casam com
    código nenhum — é o que os torna inofensivos. Nenhum destes 4 prefixos
    existe na tabela, ainda que sejam prefixos de códigos que existem."""
    assert buscar_reducao_por_prefixo(conexao, ["9018", "8713", "87", "90"]) == []


def test_lookup_traz_o_anexo_ordem_da_coluna(conexao):
    linhas = buscar_reducao_por_prefixo(conexao, ["06", "04051000"])

    assert {linha.anexo: linha.anexo_ordem for linha in linhas} == {"XV": 15, "I": 1}


def test_lookup_traz_a_alinea_dos_itens_19_e_20_do_anexo_i(conexao):
    linhas = buscar_reducao_por_prefixo(conexao, ["0207", "0302"])

    assert {linha.item: linha.alinea for linha in linhas} == {19: "d", 20: "a"}


def test_prefixo_compartilhado_devolve_as_tres_linhas(conexao):
    """A sobreposição tripla do Anexo XII precisa chegar inteira ao Python — é
    lá que o desempate acontece."""
    linhas = buscar_reducao_por_prefixo(conexao, ["90181980"])

    assert sorted((linha.item, linha.sub_item) for linha in linhas) == [
        (1, 2),
        (1, 3),
        (14, 0),
    ]


def test_lote_de_prefixos_resolve_em_exatamente_uma_query(conexao):
    espiao = CursorEspiao(conexao)

    linhas = buscar_reducao_por_prefixo(
        espiao, ["04051000", "06", "87131000", "90213991", "22030000"]
    )

    assert espiao.execucoes == 1
    assert {linha.anexo for linha in linhas} == {"I", "XII", "XIII", "XV"}


def test_prefixo_inexistente_devolve_lista_vazia_nao_erro(conexao):
    assert buscar_reducao_por_prefixo(conexao, ["99999999"]) == []


def test_lista_vazia_nao_abre_cursor(conexao):
    espiao = CursorEspiao(conexao)

    assert buscar_reducao_por_prefixo(espiao, []) == []
    assert espiao.execucoes == 0


# Migração 006 — remoção do código morto -------------------------------------


def test_regras_tributarias_cache_nao_existe_mais(conexao):
    """Decisão 12 do Anexo I: a tabela nunca teve linhas, nunca teve consumidor,
    e sua forma está errada para os regimes diferenciados reais."""
    with conexao.cursor() as cur:
        cur.execute("SELECT to_regclass('public.regras_tributarias_cache')")
        assert cur.fetchone()[0] is None


def test_as_migracoes_novas_ficaram_registradas(conexao):
    with conexao.cursor() as cur:
        cur.execute(
            "SELECT versao FROM schema_migrations WHERE versao IN "
            "('005_cesta_basica_anexo_i.sql', '006_remover_regras_tributarias_cache.sql', "
            "'007_generalizar_anexos_reducao_zero.sql', "
            "'008_anexos_reducao_zero_xii_xiii_xv.sql') ORDER BY versao"
        )
        versoes = [linha[0] for linha in cur.fetchall()]

    assert versoes == [
        "005_cesta_basica_anexo_i.sql",
        "006_remover_regras_tributarias_cache.sql",
        "007_generalizar_anexos_reducao_zero.sql",
        "008_anexos_reducao_zero_xii_xiii_xv.sql",
    ]
