path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old1 = '''ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "modules"))'''
new1 = '''ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "modules"))
sys.path.insert(0, str(ROOT / "rag_env" / "modules_rag"))'''

old2 = '''        if st.button("🚀 Lancer l'extraction ICP",type="primary",use_container_width=True):'''
new2 = '''        use_rag = st.checkbox("🧪 Utiliser l'extraction RAG (experimental, necessite Ollama + Qdrant lances)", value=False)
        if st.button("🚀 Lancer l'extraction ICP",type="primary",use_container_width=True):'''

old3 = '''                        if mid=="FE":
                            from icp_fe_extract import find_fe_range,extract_fe_tests
                            doc2=fitz.open(tmp_pdf)
                            try: s2,e2=find_fe_range(doc2)
                            except ValueError: s2,e2=0,doc2.page_count-1
                            text="\\n".join(doc2[p].get_text("text") for p in range(s2,e2+1)); doc2.close()
                            fe_tests=extract_fe_tests(text)
                            results["FE"]=fe_tests; st.session_state.icp_fe_limits=fe_tests'''
new3 = '''                        if mid=="FE":
                            if use_rag:
                                from ingest import extract_pages, chunk_text, index_chunks
                                from rag_extractor import extract_fe_tests_rag
                                product_id = active_prod.get("name", "UNKNOWN")
                                pages_rag = extract_pages(tmp_pdf)
                                chunks_rag = []
                                for pr in pages_rag:
                                    chunks_rag.extend(chunk_text(pr["text"], source_pdf=os.path.basename(tmp_pdf), page=pr["page"], product=product_id))
                                index_chunks(chunks_rag)
                                rag_result = extract_fe_tests_rag(tmp_pdf, product_id)
                                fe_tests = rag_result.get("FE_Tests", [])
                            else:
                                from icp_fe_extract import find_fe_range,extract_fe_tests
                                doc2=fitz.open(tmp_pdf)
                                try: s2,e2=find_fe_range(doc2)
                                except ValueError: s2,e2=0,doc2.page_count-1
                                text="\\n".join(doc2[p].get_text("text") for p in range(s2,e2+1)); doc2.close()
                                fe_tests=extract_fe_tests(text)
                            results["FE"]=fe_tests; st.session_state.icp_fe_limits=fe_tests'''

for old, new, label in [(old1, new1, "chemin RAG"), (old2, new2, "case a cocher"), (old3, new3, "branche FE")]:
    if old not in content:
        print(f"ATTENTION: bloc '{label}' introuvable, rien modifie pour ce bloc.")
        continue
    content = content.replace(old, new, 1)
    print(f"OK: bloc '{label}' modifie.")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Termine.")