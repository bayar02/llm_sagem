#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
retriever.py — Recherche hybride (vecteur + mots-clés) sur les documents indexés
====================================================================================

SCAFFOLD — squelette à compléter, non exécuté ici.

Combine :
  - recherche dense (embeddings, via Qdrant)          -> comprend le sens / la reformulation
  - recherche lexicale (BM25 sur les mêmes chunks)      -> fiable sur les codes exacts
                                                            (ex. "PT12", "Test#7", "DVB-T2")

Les documents produits contiennent beaucoup d'identifiants exacts (TestPoint,
Test#, fréquences) que la recherche purement sémantique peut mal retrouver —
d'où l'intérêt de l'hybride plutôt que du vecteur seul.

Mode "local" sans Docker : QdrantClient(path="./qdrant_local_data") fonctionne
en fichier local, pratique pour un premier essai avant de lancer docker-compose.
"""

import os
from typing import List, Dict, Any

from dotenv import load_dotenv
from rank_bm25 import BM25Okapi

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "telecom_product_docs")


def _get_client():
    from qdrant_client import QdrantClient
    return QdrantClient(url=QDRANT_URL)


def dense_search(query: str, product: str = None, top_k: int = 8) -> List[Dict[str, Any]]:
    from ingest import embed_texts  # réutilise la même fonction d'embedding que l'ingestion
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    client = _get_client()
    vec = embed_texts([query])[0]

    qfilter = None
    if product:
        qfilter = Filter(must=[FieldCondition(key="product", match=MatchValue(value=product))])

    result = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=vec,
        query_filter=qfilter,
        limit=top_k,
    )
    hits = result.points
    return [{"text": h.payload["text"], "score": h.score, "page": h.payload.get("page"),
             "source_pdf": h.payload.get("source_pdf")} for h in hits]


def bm25_search(query: str, corpus_chunks: List[Dict[str, Any]], top_k: int = 8) -> List[Dict[str, Any]]:
    """corpus_chunks : liste de {text, ...} déjà chargée en mémoire (ex. pour un seul PDF).
    Pour un corpus multi-produits volumineux, préférer un index BM25 persistant
    (ex. via Qdrant sparse vectors natifs plutôt que rank-bm25 en mémoire)."""
    tokenized_corpus = [c["text"].split() for c in corpus_chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(query.split())
    ranked = sorted(zip(corpus_chunks, scores), key=lambda x: x[1], reverse=True)
    return [{**c, "bm25_score": s} for c, s in ranked[:top_k]]


def hybrid_search(query: str, product: str = None, top_k: int = 8, alpha: float = 0.6) -> List[Dict[str, Any]]:
    """
    Fusion simple dense + lexical (reciprocal rank fusion serait une amélioration
    possible une fois le besoin validé). alpha = poids donné au score dense.

    TODO : remplacer par les sparse vectors natifs de Qdrant (BM25 intégré depuis
    v1.10) pour éviter de maintenir un index BM25 séparé en mémoire.
    """
    dense_results = dense_search(query, product=product, top_k=top_k * 2)
    # Le lexical nécessite le corpus en mémoire : à brancher sur un cache local
    # des chunks du produit concerné, ou sur les sparse vectors Qdrant (recommandé).
    return dense_results[:top_k]


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "limite de puissance RF 5GHz"
    for r in hybrid_search(q):
        print(f"[p.{r.get('page')}] {r.get('source_pdf')} (score={r.get('score'):.3f})")
        print(r["text"][:200], "...\n")
