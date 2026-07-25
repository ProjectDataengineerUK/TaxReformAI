"""A primeira ingestão real gravou a LCP 214/2025 com 35.677 caracteres de
substituição (U+FFFD) e ZERO ocorrências de "ç", num texto jurídico brasileiro
de ~1 milhão de caracteres.

Causa: o Planalto declara `charset=iso-8859-1` no **301**, mas a resposta 200
final não declara charset nenhum. Sem charset o httpx assume UTF-8; bytes
ISO-8859-1 lidos como UTF-8 viram U+FFFD, e `html.encode("utf-8")` grava a
corrupção permanentemente no data lake.

A corrupção era silenciosa: o pipeline inteiro (parse de 580 artigos, 2547
chunks, 20 min de embedding) roda normalmente sobre texto destruído. Nenhuma
etapa falha — só o resultado é inútil, e as citações mostradas ao usuário
sairiam com mojibake.
"""

from ingestion.scraper.planalto_scraper import decodificar_resposta

# "Produção de Bens e Serviços — Imposto Seletivo" em ISO-8859-1.
TRECHO_LATIN1 = "Produção de Bens e Serviços — Imposto Seletivo".encode("cp1252")
TRECHO_UTF8 = "Produção de Bens e Serviços — Imposto Seletivo".encode("utf-8")


def test_sem_charset_declarado_bytes_latin1_sao_lidos_corretamente():
    """O caso real que quebrou: resposta 200 sem charset, corpo ISO-8859-1."""
    texto = decodificar_resposta(None, TRECHO_LATIN1)

    assert "Produção" in texto
    assert "Serviços" in texto
    assert "�" not in texto, "nenhum caractere de substituição pode sobrar"


def test_sem_charset_declarado_bytes_utf8_continuam_funcionando():
    """A detecção não pode quebrar as fontes que já vinham em UTF-8."""
    texto = decodificar_resposta(None, TRECHO_UTF8)

    assert "Produção de Bens e Serviços" in texto
    assert "�" not in texto


def test_charset_declarado_e_respeitado():
    assert "Produção" in decodificar_resposta("iso-8859-1", TRECHO_LATIN1)
    assert "Produção" in decodificar_resposta("utf-8", TRECHO_UTF8)


def test_utf8_e_tentado_antes_por_falhar_alto_em_latin1():
    """UTF-8 estrito rejeita bytes latin-1 em vez de corrompê-los em silêncio —
    é exatamente essa propriedade que sustenta a ordem da cadeia. Se um dia
    alguém inverter a ordem, este teste cai."""
    try:
        TRECHO_LATIN1.decode("utf-8")
        raise AssertionError("bytes latin-1 deveriam ser inválidos em UTF-8 estrito")
    except UnicodeDecodeError:
        pass


def test_bytes_indecodificaveis_nao_explodem():
    """Último recurso: melhor um documento com um caractere trocado do que uma
    ingestão que morre. Mas só depois de as tentativas estritas falharem."""
    texto = decodificar_resposta(None, b"\x81\x8d valido \x9d")

    assert "valido" in texto


def test_documento_grande_latin1_nao_perde_acentuacao():
    """Guarda contra regressão em escala: o bug real só se revelou num
    documento de ~1 MB, onde 35.677 acentos foram perdidos de uma vez."""
    original = "Produção de Bens e Serviços com acentuação plena: ãõçéíúâê. " * 5000
    texto = decodificar_resposta(None, original.encode("cp1252"))

    assert texto.count("ç") == original.count("ç")
    assert texto.count("ã") == original.count("ã")
    assert "�" not in texto
