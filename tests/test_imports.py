"""Regression tests for the rag_env module import structure.

These tests guard against the historical bug where the local
`rag_env/modules_rag/retriever.py` module collided with an unrelated
PyPI package also named `retriever`. See project documentation for
the full history of this issue.

Run with:
    pytest -q tests/test_imports.py
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAG_MODULES_PATH = os.path.join(PROJECT_ROOT, "rag_env", "modules_rag")


def _ensure_path():
    if RAG_MODULES_PATH not in sys.path:
        sys.path.insert(0, RAG_MODULES_PATH)


def test_rag_retriever_module_exists_on_disk():
    module_path = os.path.join(RAG_MODULES_PATH, "rag_retriever.py")
    assert os.path.exists(module_path), (
        "rag_retriever.py should exist (renamed from retriever.py to avoid "
        "colliding with the unrelated PyPI 'retriever' package)"
    )


def test_old_retriever_module_removed():
    old_module_path = os.path.join(RAG_MODULES_PATH, "retriever.py")
    assert not os.path.exists(old_module_path), (
        "retriever.py should no longer exist; it was renamed to "
        "rag_retriever.py to avoid the naming collision"
    )


def test_rag_retriever_imports_from_project_root():
    _ensure_path()
    import rag_retriever
    assert hasattr(rag_retriever, "hybrid_search"), (
        "rag_retriever module must expose a hybrid_search() function"
    )


def test_rag_extractor_imports_local_rag_retriever():
    extractor_path = os.path.join(RAG_MODULES_PATH, "rag_extractor.py")
    with open(extractor_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "from rag_retriever import" in content, (
        "rag_extractor.py should import from rag_retriever, not retriever"
    )
    assert "from retriever import" not in content


def test_rag_extractor_rf_imports_local_rag_retriever():
    extractor_rf_path = os.path.join(RAG_MODULES_PATH, "rag_extractor_rf.py")
    with open(extractor_rf_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "from rag_retriever import" in content, (
        "rag_extractor_rf.py should import from rag_retriever, not retriever"
    )
    assert "from retriever import" not in content
