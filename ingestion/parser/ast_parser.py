import re

from bs4 import BeautifulSoup

from ingestion.parser.ast_models import Alinea, Artigo, Inciso, Lei, Paragrafo, Secao

_NIVEL_CANON_ORDER = ("LIVRO", "TITULO", "CAPITULO", "SECAO", "SUBSECAO")

_NIVEL_CANON = {
    "LIVRO": "LIVRO",
    "TITULO": "TITULO",
    "TÍTULO": "TITULO",
    "CAPITULO": "CAPITULO",
    "CAPÍTULO": "CAPITULO",
    "SECAO": "SECAO",
    "SEÇÃO": "SECAO",
    "SUBSECAO": "SUBSECAO",
    "SUBSEÇÃO": "SUBSECAO",
}

HEADER_RE = re.compile(
    r"^(LIVRO|T[ÍI]TULO|CAP[ÍI]TULO|SUBSE[ÇC][ÃA]O|SE[ÇC][ÃA]O)\s+([IVXLCDM]+)\b",
    re.IGNORECASE,
)
ARTIGO_RE = re.compile(r"^Art\s*\.?\s*(\d+)[ºo°]?(-[A-Z])?\b", re.IGNORECASE)
PARAGRAFO_NUM_RE = re.compile(r"^§\s*(\d+)[ºo°]?\b")
PARAGRAFO_UNICO_RE = re.compile(r"^Par[áa]grafo\s+[úu]nico\b", re.IGNORECASE)
INCISO_RE = re.compile(r"^([IVXLCDM]+)\s*[-–—]\s*")
ALINEA_RE = re.compile(r"^([a-z])\)\s*")


class ASTParseError(Exception):
    def __init__(self, message: str, trecho: str = ""):
        super().__init__(f"{message} | trecho: {trecho[:200]!r}")
        self.trecho = trecho


def _e_texto_revogado(p) -> bool:
    """O Planalto marca dispositivos vetados/revogados mantendo o texto
    original riscado (text-decoration:line-through) antes da redação vigente.
    Esses trechos NÃO podem entrar no RAG — citar lei revogada quebraria a
    garantia de auditabilidade do TaxReform AI."""
    return "line-through" in str(p)


def _paragraphs(soup: BeautifulSoup):
    for p in soup.find_all("p"):
        if _e_texto_revogado(p):
            continue
        text = p.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        yield text, p.get("align", "")


def parse_lei(html: str, documento_id: str, titulo: str, fonte_url: str) -> Lei:
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:
        raise ASTParseError("Falha ao parsear HTML", str(exc)) from exc

    lei = Lei(documento_id=documento_id, titulo=titulo, fonte_url=fonte_url)

    secao_stack: list[Secao] = []
    artigo_atual: Artigo | None = None
    paragrafo_atual: Paragrafo | None = None
    inciso_atual: Inciso | None = None
    aguardando_titulo_para: Secao | None = None

    def container_de_artigos() -> list[Artigo]:
        return secao_stack[-1].artigos if secao_stack else lei.artigos_soltos

    for text, align in _paragraphs(soup):
        header_match = HEADER_RE.match(text) if align == "center" else None

        if header_match:
            nivel_raw, numero = header_match.group(1), header_match.group(2)
            nivel = _NIVEL_CANON.get(nivel_raw.upper(), nivel_raw.upper())
            nova_secao = Secao(nivel=nivel, numero=numero, titulo="")

            while secao_stack and _NIVEL_CANON_ORDER.index(
                secao_stack[-1].nivel
            ) >= _NIVEL_CANON_ORDER.index(nivel):
                secao_stack.pop()

            if secao_stack:
                secao_stack[-1].subsecoes.append(nova_secao)
            else:
                lei.secoes.append(nova_secao)
            secao_stack.append(nova_secao)

            aguardando_titulo_para = nova_secao
            artigo_atual = paragrafo_atual = inciso_atual = None
            continue

        if (
            aguardando_titulo_para is not None
            and align == "center"
            and not ARTIGO_RE.match(text)
        ):
            aguardando_titulo_para.titulo = f"{aguardando_titulo_para.titulo} {text}".strip()
            continue
        aguardando_titulo_para = None

        artigo_match = ARTIGO_RE.match(text)
        if artigo_match:
            sufixo = artigo_match.group(2) or ""
            numero = f"{artigo_match.group(1)}{sufixo}"
            corpo = text[artigo_match.end() :].strip(" .")
            artigo_atual = Artigo(numero=numero, texto=corpo)
            container_de_artigos().append(artigo_atual)
            paragrafo_atual = inciso_atual = None
            continue

        if artigo_atual is None:
            continue

        paragrafo_match = PARAGRAFO_NUM_RE.match(text)
        paragrafo_unico_match = None if paragrafo_match else PARAGRAFO_UNICO_RE.match(text)
        if paragrafo_match or paragrafo_unico_match:
            if paragrafo_match:
                numero = paragrafo_match.group(1)
                corpo = text[paragrafo_match.end() :].strip(" .")
            else:
                numero = "único"
                corpo = text[paragrafo_unico_match.end() :].strip(" .")
            paragrafo_atual = Paragrafo(numero=numero, texto=corpo)
            artigo_atual.paragrafos.append(paragrafo_atual)
            inciso_atual = None
            continue

        inciso_match = INCISO_RE.match(text)
        if inciso_match:
            numero = inciso_match.group(1)
            corpo = text[inciso_match.end() :].strip(" .")
            inciso_atual = Inciso(numero=numero, texto=corpo)
            destino = paragrafo_atual.incisos if paragrafo_atual else artigo_atual.incisos
            destino.append(inciso_atual)
            continue

        alinea_match = ALINEA_RE.match(text)
        if alinea_match and inciso_atual is not None:
            letra = alinea_match.group(1)
            corpo = text[alinea_match.end() :].strip(" .")
            inciso_atual.alineas.append(Alinea(letra=letra, texto=corpo))
            continue

        if inciso_atual is not None:
            inciso_atual.texto = f"{inciso_atual.texto} {text}".strip()
        elif paragrafo_atual is not None:
            paragrafo_atual.texto = f"{paragrafo_atual.texto} {text}".strip()
        elif artigo_atual is not None:
            artigo_atual.texto = f"{artigo_atual.texto} {text}".strip()

    if not lei.secoes and not lei.artigos_soltos:
        raise ASTParseError("Nenhuma estrutura reconhecida no HTML fornecido", html[:500])

    return lei
