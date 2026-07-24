import datetime
from pathlib import Path

import pytest

from ingestion.chunking.chunker import gerar_chunks
from ingestion.parser.ast_parser import parse_lei

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_lei.html"


@pytest.fixture
def lei():
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    return parse_lei(
        html,
        documento_id="LCP_214_2025",
        titulo="Lei Complementar 214/2025",
        fonte_url="https://www.planalto.gov.br/ccivil_03/leis/lcp/Lcp214.htm",
    )


@pytest.fixture
def chunks(lei):
    return gerar_chunks(
        lei,
        esfera="FEDERAL_CBS_IBS",
        data_vigencia_inicio=datetime.date(2027, 1, 1),
    )


def test_gera_ao_menos_um_chunk_por_artigo(lei, chunks):
    def todos_artigos(secao):
        artigos = list(secao.artigos)
        for sub in secao.subsecoes:
            artigos.extend(todos_artigos(sub))
        return artigos

    numeros_artigos = {a.numero for s in lei.secoes for a in todos_artigos(s)}
    numeros_artigos |= {a.numero for a in lei.artigos_soltos}

    numeros_com_chunk = {c.dispositivo.split(",")[0].replace("Art. ", "") for c in chunks}
    assert numeros_artigos <= numeros_com_chunk


def test_todos_os_chunks_tem_metadados_obrigatorios(chunks):
    for chunk in chunks:
        assert chunk.documento_id == "LCP_214_2025"
        assert chunk.dispositivo
        assert chunk.esfera == "FEDERAL_CBS_IBS"
        assert chunk.data_vigencia_inicio == datetime.date(2027, 1, 1)
        assert chunk.fonte_url


def test_chunk_parent_child_artigo_sem_filhos(chunks):
    art2 = next(c for c in chunks if c.dispositivo == "Art. 2")
    assert art2.parent_texto == art2.texto
    assert "neutralidade" in art2.texto


def test_chunk_inciso_herda_contexto_do_artigo_parent(chunks):
    inciso = next(c for c in chunks if c.dispositivo == "Art. 1, Inciso I")
    assert inciso.parent_texto == "Ficam instituídos:"
    assert inciso.texto != inciso.parent_texto
    assert "Imposto sobre Bens e Serviços" in inciso.texto


def test_chunk_alinea_tem_dispositivo_granular(chunks):
    alinea = next(c for c in chunks if c.dispositivo == 'Art. 3, Inciso I, alínea "a"')
    assert alinea.parent_texto == "Para fins desta Lei Complementar, consideram-se:"


def test_pontos_qdrant_tem_id_deterministico_e_unico(chunks):
    ids = [c.qdrant_point_id() for c in chunks]
    assert len(ids) == len(set(ids)), "todo chunk deve gerar um point id único no Qdrant"
