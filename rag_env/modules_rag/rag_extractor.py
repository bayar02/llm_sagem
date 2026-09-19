#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rag_extractor.py — Extraction ICP assistée par RAG + LLM
=================================================================

SCAFFOLD — squelette à compléter, non exécuté ici.

Contexte projet :
  icp_fe_extract.py (existant) extrait les limites FE par regex sur le texte
  brut du PDF. Le fichier lui-même documente des "correctifs" répétés au fil
  du temps pour absorber les variations de mise en page entre produits
  (DIW377, DCIW378, DIW253, ...) — signe que l'approche regex est fragile
  face à des PDFs dont le format n'est pas 100% stable.

  Ce module vise à *compléter* (pas forcément remplacer) icp_fe_extract.py :
  utiliser un LLM, guidé par les passages pertinents retrouvés via RAG
  (retriever.py), pour extraire la même structure de données mais avec plus
  de robustesse aux variations de mise en page, EN CONSERVANT EXACTEMENT le
  même contrat de sortie JSON afin de rester compatible avec app.py et
  check_fe_log.py sans aucune modification côté validation des logs.

  Contrat de sortie identique à icp_fe_extract.py :
    {
      "FE_Tests": [
        {
          "Test": "Test#3",
          "Frequency": "198.5MHz",
          "Modulation": "8MHz DVB-T",
          "Limits": [
            {"Parameter": "Viterbi BER", "Min": "...", "Max": "...", "Unit": "..."},
            ...
          ]
        },
        ...
      ]
    }

Stratégie recommandée pour la mise en production :
  1. Faire tourner rag_extractor.py EN PARALLÈLE de icp_fe_extract.py sur un
     échantillon de PDFs déjà validés manuellement (ceux dans LOGS_*).
  2. Comparer les deux JSON produits (diff automatisé) pour mesurer les écarts
     avant de basculer une équipe dessus.
  3. Ne devient la voie "par défaut" dans app.py qu'après validation — garder
     icp_fe_extract.py comme filet de sécurité / fallback en cas d'échec API.
"""

import json
import os
from typing import List, Dict, Any

from dotenv import load_dotenv

from retriever import hybrid_search
from llm_router import call_llm, count_tokens

load_dotenv()

EXTRACTION_SYSTEM_PROMPT = """Tu es un expert en validation de tests pour équipements de télécommunication.
Tu extrais les limites de test FE (DVB-C, DVB-S/S2, DVB-T/T2) depuis des extraits
d'un document ICP (Inspection Control Plan) Sagemcom.

Réponds UNIQUEMENT avec un JSON valide de la forme :
{
  "FE_Tests": [
    {"Test": "Test#N", "Frequency": "...MHz", "Modulation": "... (inclure le systeme, ex: 256QAM DVB-C)",
     "Limits": [{"Parameter": "...", "Min": "...", "Max": "...", "Unit": "..."}]}
  ]
}

Paramètres attendus — utiliser EXACTEMENT ces libellés complets, jamais d'abréviations
(ne jamais écrire "BER", "UNCOR", "CN", "FO" ou "RO") :
Viterbi BER, Uncorrected blocks, RSSI, Carrier-to-Noise Ratio, Frequency Offset, Rate Offset.

Règle importante pour lire les valeurs Min/Max : chaque paramètre est suivi de deux nombres
(Min puis Max) et parfois d'une unité, IMMEDIATEMENT apres son libelle. Si tu vois ensuite,
plus loin dans le texte, une ligne isolee contenant plusieurs nombres qui ne suit pas
directement un libelle de parametre, IGNORE-la : ce n'est pas une valeur Min/Max valide,
c'est un artefact de mise en page du PDF.

Pour le parametre "Viterbi BER" specifiquement, l'unite affichee dans le document
est souvent une notation scientifique du type ".10-7" et non "dB". Si le texte
apres Min/Max pour Viterbi BER n'est pas une unite standard reconnaissable
(dB, dBm, kHz, ppm), retourne "Unit": "" (chaine vide) plutot que d'inventer "dB".

Si une limite est indiquée "N/A" dans le document, retourne "Min": "N/A", "Max": "N/A"
(ne jamais inventer de valeur numérique).
"""


def _try_repair_json(raw: str):
    """Tente de reparer un JSON tronque en ajoutant les caracteres de fermeture manquants."""
    suffixes = ["", "}", "]}", "}]}", "]}}", "}}", "]}]}", "}]}}"]
    for suf in suffixes:
        try:
            return json.loads(raw + suf)
        except json.JSONDecodeError:
            continue
    return None


def extract_fe_tests_rag(pdf_path: str, product: str) -> Dict[str, Any]:
    """
    Pipeline :
      1. Récupérer les passages pertinents via RAG (hybrid_search) plutôt que
         d'envoyer tout le PDF au LLM (économie de tokens, cf. llm_router.py).
      2. Construire un prompt avec ces passages.
      3. Appeler le LLM (via llm_router.call_llm, qui gère la bascule/quota).
      4. Parser strictement le JSON retourné, avec repli explicite en cas d'échec.
    """
    passages = hybrid_search(
        query="limites de test FE Viterbi BER RSSI Carrier-to-Noise Frequency Offset Rate Offset",
        product=product,
        top_k=6,
    )
    context = "\n---\n".join(p["text"] for p in passages)

    if "DVB" not in context.upper():
        print("[rag_extractor] Aucun marqueur DVB dans les passages recuperes - pas de section FE, retour direct d'une liste vide (LLM non appele).")
        return {"FE_Tests": []}

    user_prompt = f"Extraits pertinents du document ICP ({product}) :\n\n{context}\n\nExtrait les FE_Tests au format demandé."

    estimated = count_tokens(EXTRACTION_SYSTEM_PROMPT + user_prompt)
    print(f"[rag_extractor] tokens estimés pour cet appel : {estimated}")

    raw_response = call_llm(EXTRACTION_SYSTEM_PROMPT, user_prompt)

    try:
        return json.loads(raw_response)
    except json.JSONDecodeError as e:
        with open("last_raw_response.txt", "w", encoding="utf-8") as f:
            f.write(raw_response)
        repaired = _try_repair_json(raw_response)
        if repaired is not None:
            print("[rag_extractor] JSON tronque detecte, reparation automatique appliquee.")
            return repaired
        raise ValueError(
            f"Réponse LLM non-JSON, fallback recommandé vers icp_fe_extract.py classique. Erreur: {e}"
        )


def compare_with_classic(pdf_path: str, product: str) -> Dict[str, Any]:
    """Utilitaire de validation (étape 1 de la stratégie de mise en production) :
    exécute l'extraction RAG et l'extraction regex classique, et retourne un
    diff simple pour revue manuelle avant bascule."""
    from icp_fe_extract import extract_fe_tests  # module existant, réutilisé tel quel
    import fitz

    doc = fitz.open(pdf_path)
    text = "\n".join(doc[p].get_text("text") for p in range(doc.page_count))
    classic_result = {"FE_Tests": extract_fe_tests(text)}

    rag_result = extract_fe_tests_rag(pdf_path, product)

    return {
        "classic": classic_result,
        "rag": rag_result,
        "nb_tests_classic": len(classic_result["FE_Tests"]),
        "nb_tests_rag": len(rag_result.get("FE_Tests", [])),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python rag_extractor.py <pdf> <product_id>")
        sys.exit(1)
    result = compare_with_classic(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2, ensure_ascii=False))
