"""Baixa a TIPI oficial da RFB, extrai o texto e grava em `aliquotas_ipi_tipi`.

Roda só via `migrar_banco.yml` (guarda `MIGRAR`), nunca local — mesma
política do resto do projeto. Não usa `PdfLegalSource`/GCS: a TIPI não segue
o pipeline de ingestão para o Qdrant (é dado tabular, não legislação com
hierarquia de artigos — ver `db/tipi.py`), e sua fonte é público sem
necessidade de arquivamento próprio de lineage neste momento.
"""

import os
import subprocess
import sys
import tempfile

import httpx
import psycopg

from db.tipi import gravar_tipi, parse_tipi
from ingestion.scraper.planalto_scraper import _HEADERS, decodificar_resposta

URL_TIPI = (
    "https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/legislacao/"
    "documentos-e-arquivos/tipi.pdf"
)
DISPOSITIVO_LEGAL = (
    "Decreto nº 11.158/2022 (TIPI) e atualizações posteriores — "
    "Ato Declaratório Executivo RFB nº 1/2026 (última verificada)"
)


def main() -> None:
    print(f"Baixando TIPI de {URL_TIPI}")
    resposta = httpx.get(URL_TIPI, headers=_HEADERS, timeout=60, follow_redirects=True)
    resposta.raise_for_status()
    pdf_bytes = resposta.content
    print(f"PDF baixado: {len(pdf_bytes)} bytes")

    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()
        resultado = subprocess.run(
            ["pdftotext", "-layout", tmp.name, "-"],
            capture_output=True,
            timeout=60,
            check=True,
        )
    # pdftotext devolve bytes; a TIPI não declara charset (mesma armadilha do
    # Planalto), então a mesma detecção de encoding se aplica aqui.
    texto = decodificar_resposta(None, resultado.stdout)

    linhas = parse_tipi(texto)
    if not linhas:
        print("FALHA: nenhum código NCM extraído do PDF — o layout pode ter mudado.", file=sys.stderr)
        sys.exit(1)

    print(f"Códigos NCM extraídos: {len(linhas)}")
    nao_tributados = sum(1 for linha in linhas if linha.nao_tributado)
    print(f"  não tributados (NT): {nao_tributados}")
    print(f"  com alíquota: {len(linhas) - nao_tributados}")

    conexao = psycopg.connect(os.environ["DATABASE_URL"])
    gravados = gravar_tipi(conexao, linhas, DISPOSITIVO_LEGAL)

    # Confere a contagem real na tabela, não só o que foi tentado: gravar_tipi
    # devolve len(linhas) independente de o commit ter persistido de fato.
    with conexao.cursor() as cur:
        cur.execute("SELECT count(*) FROM aliquotas_ipi_tipi")
        total_na_tabela = cur.fetchone()[0]
    conexao.close()

    print(f"OK: {gravados} códigos processados; {total_na_tabela} linhas na tabela agora.")
    if total_na_tabela < gravados:
        print(
            f"AVISO: {gravados} códigos foram processados mas só {total_na_tabela} "
            "estão na tabela — investigar antes de confiar nestes dados.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — borda de CLI, qualquer falha vira exit 1 com mensagem
        print(f"FALHA: {exc}", file=sys.stderr)
        sys.exit(1)
