"""Diagnóstico barato: o corpus já ingerido no Qdrant reflete a LC 227/2026?

Motivado por `.claude/sdd/features/DEFINE_LC_227_2026_ATUALIZACAO_LEGAL.md`: a LC
227/2026 (13/01/2026) alterou 244 dispositivos efetivos da LCP 214/2025, mas os
logs de CI disponíveis só provam recuperação de dispositivos que NÃO mudaram —
não é evidência de que o texto pós-LC-227 foi indexado.

Marcadores usados, ambos confirmados contra fonte primária (legis.senado.leg.br)
nesta investigação — nenhum dos dois existe no texto da Publicação Original de
16/01/2025, então a presença de qualquer um prova ingestão pós-LC-227:

  1. "341-A" como dispositivo — artigo inteiramente novo (não existe sufixo "-A"
     na lei original).
  2. O texto literal do Art. 344, Parágrafo Único, Inciso IV — acréscimo da
     LC 227/2026, não uma alteração de um inciso pré-existente.

Não decide nada sozinho: só imprime o veredito para leitura humana. Reingestão
(se necessária) é decisão separada, tomada com o resultado deste script em mãos.

Roda só via `ingestao.yml`, nunca local — mesma política do resto do projeto.
"""

from __future__ import annotations

import os
import sys

DOCUMENTO_ID = "LCP_214_2025"
MARCADOR_ARTIGO_NOVO = "341-A"
MARCADOR_TEXTO_INCISO_IV = "alíquotas de referência do IBS para fins do disposto"


def main() -> None:
    from qdrant_client import QdrantClient
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    url = os.environ["QDRANT_URL"]
    api_key = os.environ["QDRANT_API_KEY"]
    collection = os.environ.get("QDRANT_COLLECTION_NAME", "legislacao_tributaria")

    client = QdrantClient(url=url, api_key=api_key)

    filtro_documento = Filter(
        must=[FieldCondition(key="documento_id", match=MatchValue(value=DOCUMENTO_ID))]
    )

    total_documento = client.count(
        collection_name=collection, count_filter=filtro_documento, exact=True
    ).count
    print(f"Documento '{DOCUMENTO_ID}': {total_documento} chunks indexados")
    if total_documento == 0:
        print(f"FALHA: nenhum chunk de {DOCUMENTO_ID} na coleção.", file=sys.stderr)
        sys.exit(1)

    # Scroll completo do documento — mais direto e menos ambíguo que embedding
    # search para uma pergunta binária (achou o texto literal ou não achou).
    encontrado_artigo_novo = False
    encontrado_inciso_iv = False
    dispositivo_art_344 = None
    offset = None
    while True:
        pontos, offset = client.scroll(
            collection_name=collection,
            scroll_filter=filtro_documento,
            limit=200,
            offset=offset,
            with_payload=True,
        )
        for ponto in pontos:
            payload = ponto.payload or {}
            dispositivo = payload.get("dispositivo") or ""
            texto = payload.get("texto") or ""

            if MARCADOR_ARTIGO_NOVO in dispositivo:
                encontrado_artigo_novo = True
                print(f"  ACHOU artigo novo: dispositivo={dispositivo!r}")

            if MARCADOR_TEXTO_INCISO_IV in texto:
                encontrado_inciso_iv = True
                print(f"  ACHOU inciso IV: dispositivo={dispositivo!r}")

            if dispositivo.startswith("Art. 344"):
                dispositivo_art_344 = dispositivo_art_344 or []
                dispositivo_art_344.append(dispositivo)

        if offset is None:
            break

    print()
    print(f"Dispositivos do Art. 344 encontrados no corpus: {dispositivo_art_344 or '(nenhum)'}")
    print()
    print("=" * 60)
    if encontrado_artigo_novo or encontrado_inciso_iv:
        print(
            "VEREDITO: corpus JÁ REFLETE a LC 227/2026 "
            f"(art. novo={encontrado_artigo_novo}, inciso IV={encontrado_inciso_iv}). "
            "Nenhuma reingestão necessária por causa desta lei."
        )
    else:
        print(
            "VEREDITO: corpus NÃO contém nenhum dos dois marcadores da LC 227/2026 — "
            "aparenta estar DESATUALIZADO em relação à lei vigente. Reingestão do "
            f"documento {DOCUMENTO_ID} recomendada antes de confiar em citações "
            "desses dispositivos."
        )
    print("=" * 60)


if __name__ == "__main__":
    main()
