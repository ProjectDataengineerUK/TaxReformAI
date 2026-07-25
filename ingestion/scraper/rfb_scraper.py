"""Receita Federal — Soluções de Consulta COSIT/Disit, via sistema SIJUT2.

Segunda fonte do blueprint (contexto.md, seção 4.1) a ser implementada, depois
do CGIBS. As Soluções de Consulta têm efeito vinculante para a RFB a partir da
publicação, então são a base da promessa de "citando fontes oficiais" para as
perguntas conversacionais do `/consulta`.

Investigação do SIJUT2 (2026-07-25), que definiu este desenho:

- O formulário é **GET** em `consulta.action`, com `termoBusca`, `ano_ato`,
  `dt_inicio`/`dt_fim` e `tiposAtosSelecionados` — filtro cabe na URL.
- **Não há API nem export público**: `/api/*` em `normasinternet2` devolve 403,
  e o bundle da SPA é construído em torno de `/auth`, `/usuario-logado` e
  `/certificado/url` (autenticação com certificado digital).
- Escopar por assunto dispensa paginação: `termoBusca=Lei Complementar 214`
  devolveu 73 atos numa única página, com as ementas inline.

Daí a decisão de ingerir **ementas**, não textos integrais: o texto completo
está atrás da SPA autenticada, e a ementa é pública, é o resumo vinculante do
ato, e traz número, órgão e data — citação auditável por si só.
"""

from datetime import UTC, datetime
from urllib.parse import urlencode

from ingestion.scraper.planalto_scraper import _HEADERS, decodificar_resposta
from ingestion.storage.raw_storage import RawStorage

URL_CONSULTA = "http://normas.receita.fazenda.gov.br/sijut2consulta/consulta.action"

# 72 = "Solução de Consulta" na taxonomia de tipos de ato do SIJUT2.
TIPO_ATO_SOLUCAO_CONSULTA = "72"


def montar_url_busca(
    termo_busca: str,
    *,
    tipo_ato: str = TIPO_ATO_SOLUCAO_CONSULTA,
    ano_ato: str | None = None,
) -> str:
    """Monta a URL de consulta. Sem paginação de propósito: o escopo por termo
    mantém o resultado numa página só, e inventar paginação para um problema
    que não existe custaria estado e incrementalidade sem ganho."""
    parametros = {
        "tiposAtosSelecionados": tipo_ato,
        "termoBusca": termo_busca,
        "tipoConsulta": "formulario",
    }
    if ano_ato:
        parametros["ano_ato"] = ano_ato
    return f"{URL_CONSULTA}?{urlencode(parametros)}"


class RFBScraper:
    """Implementação de `LegalSource` para o SIJUT2.

    Devolve o HTML da página de resultados — que contém muitos atos, não um.
    `LegalSource.fetch()` nunca exigiu que o conteúdo fosse um documento único;
    quem dá sentido a ele é o parser (`ementa_parser.parse_ementas`).
    """

    def __init__(
        self,
        storage: RawStorage,
        timeout_seconds: int = 30,
        max_retries: int = 3,
    ):
        self._storage = storage
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    def fetch(self, url: str, documento_id: str) -> tuple[str, str]:
        import httpx

        last_error: Exception | None = None
        for tentativa in range(1, self._max_retries + 1):
            try:
                response = httpx.get(
                    url,
                    timeout=self._timeout_seconds,
                    headers=_HEADERS,
                    follow_redirects=True,
                )
                response.raise_for_status()
                # Mesma detecção de charset do Planalto: sites .gov.br antigos
                # frequentemente não declaram encoding, e assumir UTF-8 destrói
                # toda a acentuação em silêncio.
                html = decodificar_resposta(response.charset_encoding, response.content)
                break
            except httpx.HTTPError as exc:
                last_error = exc
                if tentativa == self._max_retries:
                    raise RuntimeError(
                        f"Falha ao consultar {url} após {self._max_retries} tentativas: "
                        f"{type(last_error).__name__}: {last_error}"
                    ) from last_error
        else:
            raise RuntimeError(f"Falha ao consultar {url}")

        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = f"raw/rfb/{documento_id}/{timestamp}.html"
        uri = self._storage.save(path, html.encode("utf-8"))
        return html, uri
