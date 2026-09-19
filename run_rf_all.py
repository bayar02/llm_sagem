import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), "rag_env", "modules_rag"))

from rag_extractor_rf import compare_rf_with_classic

PRODUCTS = {
    "DCIW377_DISH": r"C:\Users\LENOVO\Downloads\Doc produits\Doc produits\LOGS_DISH\LOGS_DISH\ICP_PRODUCT_DISH_DCIW377_v0.4.pdf",
    "DIW377_ALTICE": r"C:\Users\LENOVO\Downloads\Doc produits\Doc produits\LOGS_377_ALTICE\LOGS_377_ALTICE\ICP_PRODUCT_ALTICE_DIW377_v1.4.pdf",
    "DCIW378_EST": r"C:\Users\LENOVO\Downloads\Doc produits\Doc produits\LOGS_DCIW378_EST\LOGS_DCIW378_EST\ICP_PRODUCT_VODAFONE_DCIW378_EST_v1.1.pdf",
    "DIW253_VF_PT": r"C:\Users\LENOVO\Downloads\Doc produits\Doc produits\LOGS_M253_VF_PT\LOGS_M253_VF_PT\ICP_PRODUCT_VODAFONE_DIW253_v0.3.pdf",
}

summary = []

for product, pdf_path in PRODUCTS.items():
    print(f"\n=== {product} ===")
    try:
        result = compare_rf_with_classic(pdf_path, product)
    except Exception as e:
        print(f"ERREUR sur {product}: {e}")
        summary.append((product, "ERREUR", str(e)))
        continue

    out_file = f"rf_compare_{product}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    nb_classic = result.get("nb_entries_classic")
    nb_rag = result.get("nb_entries_rag")

    rag_tests = result.get("rag", {}).get("RF_Tests", [])
    band_counts = {}
    for t in rag_tests:
        b = t.get("Band", "?")
        band_counts[b] = band_counts.get(b, 0) + 1

    classic_bands = result.get("classic", {})
    classic_band_counts = {b: len(v) for b, v in classic_bands.items()}

    print(f"classique total: {nb_classic} {classic_band_counts}")
    print(f"rag total: {nb_rag} {band_counts}")
    print(f"resultat complet sauvegarde dans {out_file}")

    summary.append((product, nb_classic, nb_rag))

print("\n=== RESUME ===")
for row in summary:
    print(row)