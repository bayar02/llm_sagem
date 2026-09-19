import sys, os, json
sys.path.insert(0, os.path.join(os.getcwd(), "rag_env", "modules_rag"))
sys.path.insert(0, os.path.join(os.getcwd(), "modules"))

from rag_extractor_rf import compare_rf_with_classic

pdf_path = r"C:\Users\LENOVO\Downloads\Doc produits\Doc produits\LOGS_DIW252_LOWI\LOGS_DIW252_LOWI\ICP_PRODUCT_LOWI_DIW252_v0.2.pdf"
product = "DIW252_LOWI"

result = compare_rf_with_classic(pdf_path, product)
print(json.dumps(result, indent=2, ensure_ascii=False))