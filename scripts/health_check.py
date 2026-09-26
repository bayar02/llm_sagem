#!/usr/bin/env python3
"""Basic local environment health check for telecom_validator + rag_env.

Run with:
    python scripts/health_check.py

This script performs read-only checks and never modifies data.
It is safe to run repeatedly.
"""
import importlib
import importlib.util
import os
import sys

RESULTS = []


def check(label, fn):
    try:
        fn()
        RESULTS.append((True, label, ""))
    except Exception as exc:  # noqa: BLE001
        RESULTS.append((False, label, str(exc)))


def check_python_version():
    if sys.version_info < (3, 9):
        raise RuntimeError(f"Python 3.9+ required, found {sys.version}")


def check_core_packages():
    required = ["streamlit", "fitz", "requests"]
    missing = [pkg for pkg in required if importlib.util.find_spec(pkg) is None]
    if missing:
        raise RuntimeError(f"Missing packages: {', '.join(missing)}")


def check_rag_packages():
    required = ["qdrant_client", "sentence_transformers", "rank_bm25"]
    missing = [pkg for pkg in required if importlib.util.find_spec(pkg) is None]
    if missing:
        raise RuntimeError(
            f"Missing RAG packages: {', '.join(missing)} "
            "(pip install -r rag_env/requirements_rag.txt)"
        )


def check_local_rag_imports():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rag_modules_path = os.path.join(project_root, "rag_env", "modules_rag")
    if rag_modules_path not in sys.path:
        sys.path.insert(0, rag_modules_path)
    import rag_retriever  # noqa: F401
    if not hasattr(rag_retriever, "hybrid_search"):
        raise RuntimeError("rag_retriever module does not expose hybrid_search()")


def check_ollama():
    import requests
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    resp = requests.get(f"{base_url}/api/tags", timeout=5)
    resp.raise_for_status()


def check_qdrant():
    import requests
    qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    resp = requests.get(f"{qdrant_url}/collections", timeout=5)
    resp.raise_for_status()


def check_env_file_present():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(project_root, "rag_env", ".env")
    if not os.path.exists(env_path):
        raise RuntimeError(
            "rag_env/.env not found. Copy .env.example to rag_env/.env and fill it in."
        )


def main():
    check("Python version", check_python_version)
    check("Core packages (streamlit, fitz, requests)", check_core_packages)
    check("RAG packages (qdrant_client, sentence_transformers, rank_bm25)", check_rag_packages)
    check("Local RAG module imports (rag_retriever)", check_local_rag_imports)
    check(".env file present", check_env_file_present)
    check("Ollama reachable", check_ollama)
    check("Qdrant reachable", check_qdrant)

    print("\n=== Health check results ===")
    all_ok = True
    for ok, label, detail in RESULTS:
        status = "[OK]" if ok else "[FAIL]"
        line = f"{status} {label}"
        if not ok:
            all_ok = False
            line += f" -> {detail}"
        print(line)

    print()
    if all_ok:
        print("All checks passed. You can run: streamlit run app.py")
        sys.exit(0)
    else:
        print("Some checks failed. Fix the issues above before running the app.")
        sys.exit(1)


if __name__ == "__main__":
    main()
