"""Comitê Gestor do IBS (CGIBS) — terceira fonte legal.

É a fonte que o blueprint (contexto.md, seção 4.1) mapeia como "Resoluções
estaduais/municipais consolidadas e tabelas de alíquotas por ente federativo",
e a mais relevante para o motor de cálculo: a Resolução CGIBS nº 6/2026
regulamenta o IBS em 252 páginas e 617 artigos, com "Seção VI - Das Alíquotas"
e "Subseção III - Do Recolhimento na Liquidação Financeira (Split Payment)".

Cada artigo do regulamento cita o dispositivo correspondente da LC 214/2025
(ex.: "Art. 2º ... (Art. 3º da LC 214/2025)"), o que dá referência cruzada
entre as duas fontes já ingeridas.

O documento é PDF, então `PdfLegalSource` e `parse_resolucao` — escritos para
o TCU — atendem sem modificação.
"""

from dataclasses import dataclass
from urllib.parse import urljoin

from ingestion.scraper.pdf_source import PdfLegalSource
from ingestion.storage.raw_storage import RawStorage

URL_LISTAGEM = "https://www.cgibs.gov.br/resolucoes"


class CGIBSScraper(PdfLegalSource):
    def __init__(
        self,
        storage: RawStorage,
        timeout_seconds: int = 30,
        max_retries: int = 3,
    ):
        super().__init__(
            storage,
            prefixo_storage="cgibs",
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )


@dataclass(frozen=True)
class ResolucaoCGIBS:
    numero: int
    titulo: str
    url: str

    @property
    def documento_id(self) -> str:
        return f"CGIBS_RES_{self.numero}_2026"


def listar_resolucoes(html: str, base_url: str = URL_LISTAGEM) -> list[ResolucaoCGIBS]:
    """Descobre as resoluções publicadas na página de listagem do CGIBS.

    A listagem é uma página única, sem paginação, com um link por PDF. Preferir
    descoberta a URLs fixas: as resoluções são numeradas sequencialmente e
    novas aparecem sem aviso — uma lista fixa envelheceria em silêncio.

    Links sem número identificável são ignorados em vez de virarem exceção: uma
    resolução nova com título fora do padrão não pode derrubar a ingestão das
    outras doze.
    """
    import re

    from bs4 import BeautifulSoup

    # Os títulos publicados são inconsistentes — conferido na página real:
    #   "Resolução CSIBS nº 1"   (sigla errada na origem: CSIBS, não CGIBS)
    #   "Res CGIBS N 6"          ("Res" abreviado, sem "olução")
    #   "Resolução CGIBS 7"      (sem "nº" nenhum)
    #   "Resoluçao CGIBS N 10"   ("Resoluçao", sem til)
    # Exigir "Resolução ... nº" perderia 3 das 13 em silêncio, entre elas a
    # nº 6, que é a que regulamenta o IBS. Ancorar só na sigla + número é o
    # que sobrevive a essa variação.
    padrao_numero = re.compile(r"c[sg]ibs\s*n?[º°.]?\s*(\d+)", re.IGNORECASE)

    resolucoes: dict[int, ResolucaoCGIBS] = {}
    for link in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        href = link["href"]
        if not href.lower().endswith(".pdf"):
            continue
        titulo = " ".join(link.get_text(" ", strip=True).split())
        # Título primeiro, URL como reserva: a nº 7 tem o número só no título
        # ("Resolução CGIBS 7"), e o arquivo dela não traz numeração no nome.
        encontrado = padrao_numero.search(titulo) or padrao_numero.search(href)
        if not encontrado:
            continue
        numero = int(encontrado.group(1))
        # Se a mesma resolução aparecer duas vezes, a primeira ocorrência vence:
        # a listagem está em ordem cronológica e republicações vêm depois.
        resolucoes.setdefault(
            numero,
            ResolucaoCGIBS(numero=numero, titulo=titulo, url=urljoin(base_url, href)),
        )

    return sorted(resolucoes.values(), key=lambda r: r.numero)
