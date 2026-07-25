"""Parser das ementas de Soluções de Consulta da RFB (sistema SIJUT2).

Difere estruturalmente das outras fontes. Planalto e CGIBS/TCU entregam **um
documento** com hierarquia (artigos, incisos, alíneas); o SIJUT2 entrega **uma
página de resultados** com muitos atos independentes, cada um representado por
sua ementa — o resumo vinculante do ato.

O mapeamento para o modelo AST existente é direto: a página de resultados vira
uma `Lei`, e cada Solução de Consulta vira um `Artigo` sem filhos. Assim
chunker, embedder e indexer seguem valendo sem alteração, como já valiam para
o TCU e o CGIBS.

Por que só ementas: o texto integral de cada ato mora numa SPA
(`normasinternet2.receita.fazenda.gov.br/#/consulta/externa/{id}`) cuja API
responde 403 e é construída em torno de autenticação com certificado digital.
A ementa é pública, vem inline no HTML do resultado, e traz número, órgão,
data de publicação e assunto — citação legítima e auditável.
"""

from dataclasses import dataclass

from ingestion.parser.ast_models import Artigo, Lei

PREFIXO_DISPOSITIVO = "Solução de Consulta nº"


class EmentaParseError(Exception):
    pass


@dataclass(frozen=True)
class Ementa:
    tipo_ato: str
    numero: str
    orgao: str
    publicacao: str
    texto: str

    @property
    def dispositivo(self) -> str:
        """Identificação usada na citação. Inclui o órgão porque o número
        sozinho não é único: a Cosit e cada Disit numeram em séries próprias,
        então existem várias "Solução de Consulta nº 6006"."""
        return f"{self.numero} ({self.orgao}, {self.publicacao})"


def extrair_ementas(html: str) -> list[Ementa]:
    """Lê a tabela de resultados do SIJUT2.

    Colunas, na ordem: Tipo do ato | Nº do ato | Órgão/unidade | Publicação |
    Ementa. Linhas com número de colunas diferente são ignoradas em vez de
    virarem exceção — a página traz outras tabelas (facetas, ordenação), e uma
    delas mudando não pode derrubar a ingestão.
    """
    from bs4 import BeautifulSoup

    sopa = BeautifulSoup(html, "html.parser")
    for tag in sopa(["script", "style"]):
        tag.decompose()

    ementas: list[Ementa] = []
    for linha in sopa.select("table tr"):
        celulas = linha.find_all(["td", "th"])
        if len(celulas) != 5:
            continue
        valores = [" ".join(c.get_text(" ", strip=True).split()) for c in celulas]
        tipo, numero, orgao, publicacao, texto = valores

        # Descarta o cabeçalho e qualquer linha sem conteúdo de ementa.
        if tipo.lower().startswith("tipo do ato") or not texto:
            continue
        if not numero:
            continue

        ementas.append(
            Ementa(
                tipo_ato=tipo,
                numero=numero,
                orgao=orgao,
                publicacao=publicacao,
                texto=texto,
            )
        )
    return ementas


def total_declarado(html: str) -> int | None:
    """Lê o "Total de atos localizados: N" que o SIJUT2 imprime no resultado."""
    import re

    from bs4 import BeautifulSoup

    sopa = BeautifulSoup(html, "html.parser")
    for tag in sopa(["script", "style"]):
        tag.decompose()
    encontrado = re.search(
        r"Total de atos localizados:\s*([\d.]+)", sopa.get_text(" ", strip=True)
    )
    if not encontrado:
        return None
    return int(encontrado.group(1).replace(".", ""))


def parse_ementas(texto: str, documento_id: str, titulo: str, fonte_url: str) -> Lei:
    """Mesma assinatura de `parse_lei`/`parse_resolucao`, para o pipeline não
    precisar saber qual fonte está processando."""
    ementas = extrair_ementas(texto)
    if not ementas:
        raise EmentaParseError(
            "Nenhuma ementa encontrada no resultado do SIJUT2. A consulta pode não "
            "ter retornado atos, ou a estrutura da tabela de resultados mudou."
        )

    # A busca do SIJUT2 casa palavras soltas: "Contribuição sobre Bens e
    # Serviços" devolve 2269 atos, "reforma tributária" 463. Acima do tamanho
    # de página o resultado vem truncado, e ingerir a página 1 de 30 achando
    # que ingeriu tudo é o pior tipo de falha — silenciosa e plausível.
    # Este projeto já teve uma dessas (acentuação corrompida sem nenhum erro).
    # Não implementamos paginação de propósito; então falhamos alto.
    total = total_declarado(texto)
    if total is not None and total > len(ementas):
        raise EmentaParseError(
            f"O SIJUT2 declara {total} atos mas só {len(ementas)} vieram nesta "
            "página: o resultado está truncado e a paginação não é suportada. "
            "Estreite o termo de busca (ex.: 'Lei Complementar 214, de 2025' "
            f"devolve 28) em vez de ingerir um recorte parcial silencioso."
        )

    return Lei(
        documento_id=documento_id,
        titulo=titulo,
        fonte_url=fonte_url,
        artigos_soltos=[
            Artigo(numero=e.dispositivo, texto=f"{e.tipo_ato} — {e.texto}")
            for e in ementas
        ],
    )
