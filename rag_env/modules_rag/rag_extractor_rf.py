#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rag_extractor_rf.py - Extraction RAG des limites RF Wi-Fi / Bluetooth
Miroir de rag_extractor.py (module FE) mais pour le module RF.
Une extraction distincte par bande (Bluetooth, 2.4GHz, 5GHz) pour limiter
la taille du contexte envoye au LLM a chaque appel.
Format RAG simplifie et uniforme (comme pour FE), different du schema varie
de icp_wifi_extract.py (EntryKind/Power Target/RX Power (dBm)/...).
Comparaison visuelle, comme pour le module FE.
"""

import sys
import json
from typing import Dict, Any, List

from rag_retriever import hybrid_search
from llm_router import call_llm, count_tokens
from icp_wifi_extract import extract_rf_limits


EXTRACTION_SYSTEM_PROMPT_RF = """Tu es un expert en validation de tests RF pour equipements de telecommunication.
Tu extrais les limites de test RF (Wi-Fi ou Bluetooth) depuis des extraits d\'un document
ICP (Inspection Control Plan) Sagemcom.

Reponds UNIQUEMENT avec un JSON valide de la forme :
{
  "RF_Tests": [
    {"Test": "...", "Frequency": "...MHz", "Modulation": "...",
     "Limits": [{"Parameter": "...", "Min": "...", "Max": "...", "Unit": "..."}]}
  ]
}

Pour le champ "Test" : recopie EXACTEMENT le libelle du test tel qu'il apparait dans le
document (ex. son nom de code reel comme on le voit dans le texte). N'ecris jamais un texte
generique, un exemple, ou une description a la place -- chaque entree doit avoir un libelle
different et reel. Ne combine jamais plusieurs tests avec une virgule dans ce champ.

Parametres possibles - utiliser EXACTEMENT ces libelles, jamais d\'abreviations :
Power, EVM, Frequency Tolerance, LO Leakage, PER, RX Power, Frequency drift, Max drift rate,
Frequency deviation df2, Frequency stability.

Regle importante pour lire les valeurs Min/Max : chaque parametre est suivi de ses valeurs
(Min puis Max, ou une valeur cible unique) IMMEDIATEMENT apres son libelle. Si tu vois ensuite
une ligne isolee de nombres qui ne suit pas directement un libelle de parametre, IGNORE-la :
c\'est un artefact de mise en page du PDF.

Attention, cas frequent en RF : un parametre peut etre suivi de TROIS nombres dans cet ordre
precis : Target (valeur cible), Min, Max -- et non de deux. Le JSON attend uniquement Min et
Max : ce sont le 2eme et le 3eme nombre de la sequence, jamais les deux premiers. Ne confonds
jamais Target avec Min.

Exemple d'application : si le texte affiche "Power 5 2 7.5 dBm" pour un parametre Power, cela
correspond a Target=5, Min=2, Max=7.5 -- tu dois retourner Min:"2", Max:"7.5". Ne retourne
JAMAIS Min:"5" dans ce cas.

Cas particulier "RX Power" : ce parametre est souvent une valeur UNIQUE de sensibilite (un seul
nombre en dBm), pas une paire Min/Max. Si tu ne vois qu'un seul nombre pour RX Power, mets ce
meme nombre en Min ET en Max. Le parametre "PER" (en %) est une paire Min/Max SEPAREE et
distincte de RX Power -- ne melange jamais les deux parametres, et n'utilise jamais une valeur
de PER pour completer RX Power ou inversement.

Si une limite est indiquee "N/A" ou absente dans le document, retourne "Min": "NA", "Max": "NA"
(ne jamais inventer de valeur numerique).
"""


def _try_repair_json(raw: str):
    suffixes = ["", "}", "]}", "}]}", "]}}", "}}", "]}]}", "}]}}"]
    for suf in suffixes:
        try:
            return json.loads(raw + suf)
        except json.JSONDecodeError:
            continue
    return None


BAND_QUERIES = {
    "Bluetooth": "limites de test Bluetooth TX RX Power EVM PER PRBS DH5",
    "2.4GHz": "limites de test Wi-Fi 2.4GHz TX RX Power EVM Frequency Tolerance LO Leakage PER MCS HT",
    "5GHz": "limites de test Wi-Fi 5GHz TX RX Power EVM Frequency Tolerance LO Leakage PER MCS vHT",
}


def _classify_passage_band(text: str) -> str:
    import re
    t = text.upper()
    freqs = [int(x) for x in re.findall(r"(\d{4})\s*MHZ", t)]
    has_5g_freq = any(f >= 4900 for f in freqs)
    has_24_freq = any(2400 <= f <= 2500 for f in freqs)
    has_vht = "VHT" in t
    has_bt_kw = any(kw in t for kw in ["BLUETOOTH", "DH5", "LE 1M", "PRBS", "TX_BR", "TX_BLE", "RX_BR", "RX_BLE"])
    has_wifi24_kw = ("MCS" in t) and not has_vht
    has_5g_kw = has_vht or "5GHZ" in t or "802.11AC" in t or "802.11AX" in t

    if has_5g_freq or has_5g_kw:
        return "5GHz"
    if has_bt_kw and not has_wifi24_kw:
        return "Bluetooth"
    if has_wifi24_kw and not has_bt_kw:
        return "2.4GHz"
    if has_bt_kw and has_wifi24_kw:
        return "ambiguous"
    if has_24_freq:
        return "ambiguous"
    return "unknown"


def _extract_band_rag(pdf_path: str, product: str, band: str) -> List[dict]:
    passages = hybrid_search(query=BAND_QUERIES[band], product=product, top_k=10)

    filtered = [p for p in passages if _classify_passage_band(p["text"]) in (band, "unknown")]
    dropped = len(passages) - len(filtered)
    print(f"[rag_extractor_rf] bande {band} - passages gardes : {len(filtered)}/{len(passages)} ({dropped} ecartes par classification de bande)")

    if not filtered:
        print(f"[rag_extractor_rf] bande {band} - AUCUN passage correctement classe, fallback sur les passages bruts.")
        filtered = passages

    context = "\n---\n".join(p["text"] for p in filtered)

    user_prompt = f"Extraits pertinents du document ICP ({product}), bande {band} :\n\n{context}\n\nExtrait les RF_Tests au format demande."
    estimated = count_tokens(EXTRACTION_SYSTEM_PROMPT_RF + user_prompt)
    print(f"[rag_extractor_rf] bande {band} - tokens estimes : {estimated}")

    raw_response = call_llm(EXTRACTION_SYSTEM_PROMPT_RF, user_prompt)

    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as e:
        with open(f"last_raw_response_rf_{band.replace(chr(46), chr(95))}.txt", "w", encoding="utf-8") as f:
            f.write(raw_response)
        repaired = _try_repair_json(raw_response)
        if repaired is None:
            print(f"[rag_extractor_rf] bande {band} - JSON invalide, non reparable: {e}")
            return []
        print(f"[rag_extractor_rf] bande {band} - JSON tronque, reparation appliquee.")
        parsed = repaired

    tests = parsed.get("RF_Tests", [])
    for t in tests:
        t["Band"] = band
    return tests


def extract_rf_tests_rag(pdf_path: str, product: str) -> Dict[str, Any]:
    all_tests = []
    for band in BAND_QUERIES:
        all_tests.extend(_extract_band_rag(pdf_path, product, band))
    return {"RF_Tests": all_tests}


def compare_rf_with_classic(pdf_path: str, product: str) -> Dict[str, Any]:
    classic_result = extract_rf_limits(pdf_path)
    rag_result = extract_rf_tests_rag(pdf_path, product)

    nb_classic = sum(len(v) for v in classic_result.values())
    nb_rag = len(rag_result.get("RF_Tests", []))

    return {
        "classic": classic_result,
        "rag": rag_result,
        "nb_entries_classic": nb_classic,
        "nb_entries_rag": nb_rag,
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python rag_extractor_rf.py <pdf_path> <product_id>")
        sys.exit(1)
    result = compare_rf_with_classic(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2, ensure_ascii=False))
