from pathlib import Path

import pytest

from ingestion.parser.ast_parser import ASTParseError, parse_lei

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_lei.html"


@pytest.fixture
def html_real() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def _todos_artigos(lei):
    artigos = list(lei.artigos_soltos)

    def walk(secao):
        artigos.extend(secao.artigos)
        for sub in secao.subsecoes:
            walk(sub)

    for secao in lei.secoes:
        walk(secao)
    return artigos


def test_happy_path_estrutura_completa(html_real):
    lei = parse_lei(
        html_real,
        documento_id="LCP_214_2025",
        titulo="Lei Complementar 214/2025",
        fonte_url="https://www.planalto.gov.br/ccivil_03/leis/lcp/Lcp214.htm",
    )

    assert lei.secoes, "deveria ter capturado ao menos um nível de hierarquia (Livro)"

    livro = lei.secoes[0]
    assert livro.nivel == "LIVRO"
    assert "IMPOSTO SOBRE BENS" in livro.titulo

    titulo = livro.subsecoes[0]
    assert titulo.nivel == "TITULO"

    capitulo = titulo.subsecoes[0]
    assert capitulo.nivel == "CAPITULO"
    assert "DISPOSIÇÕES PRELIMINARES" in capitulo.titulo


def test_todos_os_artigos_de_teste_sao_capturados(html_real):
    lei = parse_lei(html_real, documento_id="LCP_214_2025", titulo="x", fonte_url="https://x")
    numeros = sorted({a.numero for a in _todos_artigos(lei)})
    assert numeros == ["1", "10", "2", "3", "4", "5", "6", "7", "7-A", "8", "9"]


def test_art1_tem_incisos_diretos_no_caput(html_real):
    lei = parse_lei(html_real, documento_id="LCP_214_2025", titulo="x", fonte_url="https://x")
    art1 = next(a for a in _todos_artigos(lei) if a.numero == "1")
    assert art1.texto == "Ficam instituídos:"
    assert [i.numero for i in art1.incisos] == ["I", "II"]
    assert "Imposto sobre Bens e Serviços" in art1.incisos[0].texto


def test_edge_case_paragrafo_unico_com_incisos(html_real):
    """AT-003: artigo com estrutura aninhada complexa — incisos no caput
    (institutos possíveis) + parágrafo único com seus próprios incisos
    (regra de combinação entre eles)."""
    lei = parse_lei(html_real, documento_id="LCP_214_2025", titulo="x", fonte_url="https://x")
    art7a = next(a for a in _todos_artigos(lei) if a.numero == "7-A")
    assert [i.numero for i in art7a.incisos] == ["I", "II", "III", "IV", "V"]
    assert len(art7a.paragrafos) == 1
    assert art7a.paragrafos[0].numero == "único"
    assert [i.numero for i in art7a.paragrafos[0].incisos] == ["I", "II"]


def test_edge_case_inciso_com_alineas(html_real):
    """AT-003: inciso com alíneas aninhadas (Art. 3, Inciso I)."""
    lei = parse_lei(html_real, documento_id="LCP_214_2025", titulo="x", fonte_url="https://x")
    art3 = next(a for a in _todos_artigos(lei) if a.numero == "3")
    inciso_i = next(i for i in art3.incisos if i.numero == "I")
    assert [a.letra for a in inciso_i.alineas] == ["a", "b"]


def test_texto_revogado_riscado_e_excluido(html_real):
    """Texto com text-decoration:line-through é redação vetada/superada e não
    deve aparecer na AST — citá-la quebraria a garantia de auditabilidade."""
    lei = parse_lei(html_real, documento_id="LCP_214_2025", titulo="x", fonte_url="https://x")
    art4 = next(a for a in _todos_artigos(lei) if a.numero == "4")
    paragrafo4 = next(p for p in art4.paragrafos if p.numero == "4")
    ocorrencias = sum(1 for p in art4.paragrafos if p.numero == "4")
    assert ocorrencias == 1, "o §4º riscado (revogado) não deveria gerar um parágrafo duplicado"
    assert "ativo não circulante" in paragrafo4.texto


def test_error_case_html_sem_estrutura_reconhecida():
    with pytest.raises(ASTParseError):
        parse_lei(
            "<html><body><p>nenhum artigo aqui</p></body></html>",
            documento_id="X",
            titulo="x",
            fonte_url="https://x",
        )
