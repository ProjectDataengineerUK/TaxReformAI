import subprocess
from pathlib import Path

import pytest

from ingestion.parser.ast_parser import ASTParseError
from ingestion.parser.resolucao_parser import parse_resolucao

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "resolucao_tcu_sample.pdf"


@pytest.fixture(scope="module")
def texto_real() -> str:
    resultado = subprocess.run(
        ["pdftotext", "-layout", str(FIXTURE_PATH), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return resultado.stdout


@pytest.fixture(scope="module")
def lei(texto_real):
    return parse_resolucao(
        texto_real,
        documento_id="TCU_RES_388_2026",
        titulo="Resolução TCU 388/2026",
        fonte_url="https://rotadajurisprudencia.com.br/wp-content/uploads/2026/06/Resolucao-TCU-388_2026.pdf",
    )


def test_at001_happy_path_todos_os_16_artigos_capturados(lei):
    numeros = [a.numero for a in lei.artigos_soltos]
    assert numeros == [str(n) for n in range(1, 17)]
    assert not lei.secoes, "Resolução não tem hierarquia Livro/Título/Capítulo — só artigos_soltos"


def test_referencia_cruzada_em_minusculo_nao_vira_artigo_novo(lei):
    """Bug real encontrado contra o PDF: 'observado o disposto no art. 353, § 2º'
    quebra em linha própria após pdftotext -layout e começa com 'art.' minúsculo
    — não pode ser confundido com a definição de um novo artigo (Art. maiúsculo)."""
    art11 = next(a for a in lei.artigos_soltos if a.numero == "11")
    assert "art. 353" in art11.texto
    assert "353" not in [a.numero for a in lei.artigos_soltos]


def test_titulo_de_capitulo_e_secao_e_descartado_sem_corromper_artigo(lei):
    """Art. 5 é o último artigo do Capítulo III; o Capítulo IV + Seção I +
    seus títulos vêm antes do Art. 6 — nenhum desses deve vazar para dentro
    do texto do Art. 5 nem do Art. 6."""
    art5 = next(a for a in lei.artigos_soltos if a.numero == "5")
    art6 = next(a for a in lei.artigos_soltos if a.numero == "6")
    assert "CAPÍTULO" not in art5.paragrafos[0].texto.upper()
    assert "SEÇÃO" not in art6.texto.upper()
    assert "relatoria do Presidente" in art6.texto


def test_bloco_de_assinatura_nao_vaza_para_o_ultimo_artigo(lei):
    art16 = lei.artigos_soltos[-1]
    assert art16.numero == "16"
    assert art16.texto == "Esta Resolução entra em vigor na data de sua publicação"
    assert "VITAL DO RÊGO" not in art16.texto
    assert "Sala das Sessões" not in art16.texto


def test_at003_edge_case_paragrafo_unico_com_incisos(lei):
    art2 = next(a for a in lei.artigos_soltos if a.numero == "2")
    assert [i.numero for i in art2.incisos] == ["I", "II"]
    assert len(art2.paragrafos) == 1
    assert art2.paragrafos[0].numero == "único"
    assert [i.numero for i in art2.paragrafos[0].incisos] == ["I", "II"]


def test_at003_edge_case_multiplos_paragrafos_numerados(lei):
    art9 = next(a for a in lei.artigos_soltos if a.numero == "9")
    assert [p.numero for p in art9.paragrafos] == ["1", "2", "3"]


def test_at002_error_case_texto_sem_nenhum_artigo():
    with pytest.raises(ASTParseError):
        parse_resolucao(
            "Considerando isso e aquilo, resolve por bem não decidir nada.",
            documento_id="X",
            titulo="x",
            fonte_url="https://x",
        )
