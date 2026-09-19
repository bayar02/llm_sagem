#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ingest.py — Pipeline d'ingestion RAG pour les documents produits (ICP / MTP PDFs)
===================================================================================

SCAFFOLD — squelette prêt à compléter, non exécuté/testé sur vos vrais PDFs
(cf. décision : "Guide + scaffolding seulement").

Rôle :
  1. Extraire le texte (et éventuellement les images) des PDFs ICP/MTP
     (réutilise pdfplumber / PyMuPDF déjà présents dans requirements.txt)
  2. Découper en chunks (chunking) avec chevauchement
  3. Calculer les embeddings (Voyage AI par défaut, fallback local possible)
  4. Indexer dans Qdrant (collection définie par QDRANT_COLLECTION)

Ce module est pensé pour être appelé soit en ligne de commande, soit importé
depuis app.py comme une étape optionnelle avant l'extraction ICP classique
(icp_fe_extract.py / extract_ict_limits.py restent la voie "sans IA" existante).

Usage prévu :
    python ingest.py --pdf "ICP_PRODUCT_ALTICE_DIW377_v1.4.pdf" --product DIW377_ALTICE

TODO avant mise en service :
  - [ ] Choisir le modèle d'embedding définitif (voyage-3-lite vs bge-m3 local)
  - [ ] Décider de la stratégie OCR pour les images (voir traiter_images_page ci-dessous)
  - [ ] Ajuster CHUNK_SIZE / CHUNK_OVERLAP après tests sur 2-3 PDFs réels
  - [ ] Ajouter la déduplication (ne pas ré-indexer un PDF déjà ingéré / inchangé)
"""

import os
import uuid
import sys
import argparse
import hashlib
from dataclasses import dataclass, field
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

CHUNK_SIZE = 3000       # en caractères — à recalibrer en tokens une fois le modèle choisi
CHUNK_OVERLAP = 300

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "telecom_product_docs")
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "voyage")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "voyage-3-lite")


@dataclass
class Chunk:
    text: str
    source_pdf: str
    page: int
    product: str
    chunk_id: str = field(default="")

    def __post_init__(self):
        if not self.chunk_id:
            raw = f"{self.source_pdf}:{self.page}:{self.text[:50]}"
            self.chunk_id = str(uuid.uuid5(uuid.NAMESPACE_OID, raw))

# ─────────────────────────────────────────────────────────────
# 1. Extraction texte + images par page
# ─────────────────────────────────────────────────────────────

def extract_pages(pdf_path: str) -> List[dict]:
    """Retourne une liste de {page, text} en réutilisant fitz (déjà utilisé
    dans icp_fe_extract.py) pour rester cohérent avec le reste du projet."""
    import fitz  # PyMuPDF
    doc = fitz.open(pdf_path)
    pages = []
    for i in range(doc.page_count):
        pages.append({"page": i + 1, "text": doc[i].get_text("text")})
    return pages


def traiter_images_page(pdf_path: str, page_number: int) -> Optional[str]:
    """
    STUB — Traitement des images/diagrammes d'une page (schémas RF, captures
    d'écran de bancs de test, tableaux scannés).

    Deux pistes évoquées dans le mail à trancher selon les besoins réels :

      a) OCR classique (pytesseract + pdf2image) :
         - Bon pour du texte scanné (tableaux de limites en image plutôt qu'en
           texte sélectionnable), rapide à mettre en place.
         - Exemple d'implémentation :
             from pdf2image import convert_from_path
             import pytesseract
             images = convert_from_path(pdf_path, first_page=page_number, last_page=page_number)
             return pytesseract.image_to_string(images[0], lang="eng+fra")

      b) Détection d'objets (YOLO) :
         - Utile si le besoin est de repérer/classer des schémas, logos,
           captures d'écran spécifiques plutôt que du texte.
         - Nécessite un modèle entraîné/fine-tuné sur vos documents — investissement
           plus lourd, à réserver si l'OCR simple ne suffit pas.

    Recommandation : commencer par (a), ne passer à (b) que si des besoins de
    classification visuelle spécifiques apparaissent.
    """
    raise NotImplementedError("À implémenter selon le choix OCR vs YOLO retenu")


# ─────────────────────────────────────────────────────────────
# 2. Chunking
# ─────────────────────────────────────────────────────────────

def chunk_text(text: str, source_pdf: str, page: int, product: str) -> List[Chunk]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        piece = text[start:end].strip()
        if piece:
            chunks.append(Chunk(text=piece, source_pdf=source_pdf, page=page, product=product))
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


# ─────────────────────────────────────────────────────────────
# 3. Embeddings
# ─────────────────────────────────────────────────────────────

def embed_texts(texts: List[str]) -> List[List[float]]:
    if EMBEDDING_PROVIDER == "voyage":
        import voyageai
        client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
        result = client.embed(texts, model=EMBEDDING_MODEL, input_type="document")
        return result.embeddings
    elif EMBEDDING_PROVIDER == "local":
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("BAAI/bge-m3")
        return model.encode(texts, normalize_embeddings=True).tolist()
    else:
        raise ValueError(f"EMBEDDING_PROVIDER inconnu : {EMBEDDING_PROVIDER}")


# ─────────────────────────────────────────────────────────────
# 4. Indexation Qdrant
# ─────────────────────────────────────────────────────────────

def index_chunks(chunks: List[Chunk]):
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance

    client = QdrantClient(url=QDRANT_URL)

    vectors = embed_texts([c.text for c in chunks])
    dim = len(vectors[0]) if vectors else 1024

    if not client.collection_exists(QDRANT_COLLECTION):
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

    points = [
        PointStruct(
            id=c.chunk_id,
            vector=vec,
            payload={
                "text": c.text,
                "source_pdf": c.source_pdf,
                "page": c.page,
                "product": c.product,
            },
        )
        for c, vec in zip(chunks, vectors)
    ]
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    return len(points)


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ingestion d'un PDF produit (ICP/MTP) dans Qdrant")
    parser.add_argument("--pdf", required=True, help="Chemin du PDF à ingérer")
    parser.add_argument("--product", required=True, help="Identifiant produit (ex. DIW377_ALTICE)")
    args = parser.parse_args()

    pages = extract_pages(args.pdf)
    all_chunks: List[Chunk] = []
    for p in pages:
        all_chunks.extend(chunk_text(p["text"], source_pdf=os.path.basename(args.pdf), page=p["page"], product=args.product))

    print(f"[ingest] {len(pages)} pages -> {len(all_chunks)} chunks")

    n = index_chunks(all_chunks)
    print(f"[ingest] {n} chunks indexés dans la collection '{QDRANT_COLLECTION}'")


if __name__ == "__main__":
    main()
