import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), "rag_env", "modules_rag"))

from retriever import _get_client, QDRANT_COLLECTION

client = _get_client()

seen = {}
offset = None
while True:
    points, offset = client.scroll(
        collection_name=QDRANT_COLLECTION,
        limit=100,
        offset=offset,
        with_payload=["product", "source_pdf"],
        with_vectors=False,
    )
    for p in points:
        prod = p.payload.get("product")
        src = p.payload.get("source_pdf")
        key = (prod, src)
        seen[key] = seen.get(key, 0) + 1
    if offset is None:
        break

print("Valeurs distinctes (product, source_pdf) trouvees dans Qdrant :")
for (prod, src), count in sorted(seen.items(), key=lambda x: str(x[0])):
    print(f"  product={prod!r}  source_pdf={src!r}  ({count} chunks)")