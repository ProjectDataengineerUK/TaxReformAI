import re
from collections import Counter

from ingestion.parser.ast_models import Alinea, Artigo, Inciso, Lei, Paragrafo
from ingestion.parser.ast_parser import (
    ALINEA_RE,
    HEADER_RE,
    INCISO_RE,
    PARAGRAFO_NUM_RE,
    PARAGRAFO_UNICO_RE,
    ASTParseError,
)

_ASSINATURA_RE = "sala das sess"

# Case-sensitive (ao contrário do ARTIGO_RE de ast_parser.py): texto extraído
# de PDF via pdftotext quebra linha por largura de página, não por parágrafo
# semântico — uma referência cruzada em minúsculas no meio de uma frase (ex:
# "...observado o disposto no art. 353, § 2º...") pode cair sozinha no
# início de uma linha após a quebra. O documento real usa "Art. N" (maiúsculo)
# só para definir artigos e "art. N" (minúsculo) só para referenciar outros
# artigos — confirmado inspecionando o PDF de fixture linha a linha.
ARTIGO_DEFINICAO_RE = re.compile(r"^Art\s*\.?\s*(\d+)[ºo°]?(-[A-Z])?\b")


def _remover_rodape_repetido(linhas: list[str]) -> list[str]:
    """PDFs institucionais podem repetir cabeçalho/rodapé (nº de página,
    identificação do órgão) em cada página — HTML do Planalto não tinha esse
    ruído. Só remove linhas curtas com dígito que se repetem 3+ vezes
    (padrão de rodapé), para não arriscar apagar frases legais curtas e
    legítimas que também se repitam ocasionalmente (ex: "Parágrafo único.")."""
    contagem = Counter(linha.strip() for linha in linhas if linha.strip())
    rodapes = {
        linha
        for linha, n in contagem.items()
        if n >= 3 and len(linha) < 60 and any(c.isdigit() for c in linha)
    }
    return [linha for linha in linhas if linha.strip() not in rodapes]


def parse_resolucao(texto: str, documento_id: str, titulo: str, fonte_url: str) -> Lei:
    """Estrutura o texto de uma Resolução (extraído via pdftotext -layout) em
    Artigo/Parágrafo/Inciso/Alínea, reaproveitando os regex de ast_parser.py.

    Só popula `Lei.artigos_soltos` — Resoluções não têm a hierarquia
    Livro/Título/Capítulo/Seção da árvore AST de leis (Decision 3 do DESIGN
    de INGESTAO_TCU_E_ETL_AIRFLOW). Cabeçalhos de Capítulo/Seção são
    reconhecidos só para serem descartados (junto com seu título na linha
    seguinte), não para construir uma árvore de seções.
    """
    linhas = _remover_rodape_repetido(texto.splitlines())
    lei = Lei(documento_id=documento_id, titulo=titulo, fonte_url=fonte_url)

    artigo_atual: Artigo | None = None
    paragrafo_atual: Paragrafo | None = None
    inciso_atual: Inciso | None = None
    aguardando_titulo_secao = False

    for linha in linhas:
        text = linha.strip()
        if not text:
            continue

        if _ASSINATURA_RE in text.lower():
            break  # bloco de assinatura/data de fechamento — fim do conteúdo normativo

        if HEADER_RE.match(text):
            aguardando_titulo_secao = True
            artigo_atual = paragrafo_atual = inciso_atual = None
            continue

        if aguardando_titulo_secao:
            aguardando_titulo_secao = False
            if not ARTIGO_DEFINICAO_RE.match(text):
                continue  # título de Capítulo/Seção — descartado, fora de escopo

        artigo_match = ARTIGO_DEFINICAO_RE.match(text)
        if artigo_match:
            sufixo = artigo_match.group(2) or ""
            numero = f"{artigo_match.group(1)}{sufixo}"
            artigo_atual = Artigo(numero=numero, texto=text[artigo_match.end() :].strip(" ."))
            lei.artigos_soltos.append(artigo_atual)
            paragrafo_atual = inciso_atual = None
            continue

        if artigo_atual is None:
            continue  # preâmbulo/considerandos antes do Art. 1º — sem estrutura própria

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

    if not lei.artigos_soltos:
        raise ASTParseError("Nenhum artigo reconhecido no texto da Resolução", texto[:500])

    return lei
