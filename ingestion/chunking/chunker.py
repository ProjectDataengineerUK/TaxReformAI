from datetime import date

from ingestion.chunking.chunk_models import Chunk
from ingestion.parser.ast_models import Artigo, Inciso, Lei, Paragrafo, Secao

# Prefixo do rótulo de dispositivo. "Art." serve para leis e resoluções, mas
# não para todo tipo de ato: uma Solução de Consulta da RFB citada como
# "Art. 6006" seria uma citação FALSA, e a citação é o que o produto promete
# como auditável. Por isso é parâmetro, não literal.
PREFIXO_ARTIGO_PADRAO = "Art."


def _dispositivo_paragrafo(numero_artigo: str, paragrafo: Paragrafo) -> str:
    rotulo = "Parágrafo único" if paragrafo.numero == "único" else f"§{paragrafo.numero}"
    return f"Art. {numero_artigo}, {rotulo}"


def _dispositivo_inciso(base: str, inciso: Inciso) -> str:
    return f"{base}, Inciso {inciso.numero}"


def _dispositivo_alinea(base: str, letra: str) -> str:
    return f'{base}, alínea "{letra}"'


def _chunks_do_artigo(
    artigo: Artigo,
    *,
    documento_id: str,
    fonte_url: str,
    esfera: str,
    data_vigencia_inicio: date,
    data_vigencia_fim: date | None,
    ncm_relacionadas: list[str],
    regime: str | None,
    prefixo_dispositivo: str = PREFIXO_ARTIGO_PADRAO,
) -> list[Chunk]:
    parent_texto = artigo.texto
    chunks: list[Chunk] = []

    def novo_chunk(dispositivo: str, texto: str) -> Chunk:
        return Chunk(
            documento_id=documento_id,
            dispositivo=dispositivo,
            esfera=esfera,
            data_vigencia_inicio=data_vigencia_inicio,
            data_vigencia_fim=data_vigencia_fim,
            ncm_relacionadas=ncm_relacionadas,
            regime=regime,
            texto=texto,
            parent_texto=parent_texto,
            fonte_url=fonte_url,
        )

    tem_filhos = bool(artigo.paragrafos or artigo.incisos)
    if not tem_filhos:
        chunks.append(novo_chunk(f"{prefixo_dispositivo} {artigo.numero}", artigo.texto))
        return chunks

    for inciso in artigo.incisos:
        base = _dispositivo_inciso(f"{prefixo_dispositivo} {artigo.numero}", inciso)
        if inciso.alineas:
            for alinea in inciso.alineas:
                chunks.append(
                    novo_chunk(_dispositivo_alinea(base, alinea.letra), alinea.texto)
                )
        else:
            chunks.append(novo_chunk(base, inciso.texto))

    for paragrafo in artigo.paragrafos:
        base_paragrafo = _dispositivo_paragrafo(artigo.numero, paragrafo)
        if not paragrafo.incisos:
            chunks.append(novo_chunk(base_paragrafo, paragrafo.texto))
            continue
        for inciso in paragrafo.incisos:
            base = _dispositivo_inciso(base_paragrafo, inciso)
            if inciso.alineas:
                for alinea in inciso.alineas:
                    chunks.append(
                        novo_chunk(_dispositivo_alinea(base, alinea.letra), alinea.texto)
                    )
            else:
                chunks.append(novo_chunk(base, inciso.texto))

    return chunks


def _artigos_da_secao(secao: Secao) -> list[Artigo]:
    artigos = list(secao.artigos)
    for sub in secao.subsecoes:
        artigos.extend(_artigos_da_secao(sub))
    return artigos


def gerar_chunks(
    lei: Lei,
    *,
    esfera: str,
    data_vigencia_inicio: date,
    data_vigencia_fim: date | None = None,
    ncm_relacionadas: list[str] | None = None,
    regime: str | None = None,
    prefixo_dispositivo: str = PREFIXO_ARTIGO_PADRAO,
) -> list[Chunk]:
    """Percorre a árvore AST e gera chunks parent-child (Decision 3 do DESIGN).

    `esfera`, `data_vigencia_*`, `ncm_relacionadas` e `regime` são aplicados
    uniformemente a todos os chunks desta lei — classificação por artigo
    individual é responsabilidade do Agente Extrator de Regras (fora de
    escopo desta feature, conforme DEFINE).
    """
    artigos: list[Artigo] = list(lei.artigos_soltos)
    for secao in lei.secoes:
        artigos.extend(_artigos_da_secao(secao))

    chunks: list[Chunk] = []
    for artigo in artigos:
        chunks.extend(
            _chunks_do_artigo(
                artigo,
                documento_id=lei.documento_id,
                fonte_url=lei.fonte_url,
                esfera=esfera,
                data_vigencia_inicio=data_vigencia_inicio,
                data_vigencia_fim=data_vigencia_fim,
                ncm_relacionadas=ncm_relacionadas or [],
                regime=regime,
                prefixo_dispositivo=prefixo_dispositivo,
            )
        )
    return chunks
