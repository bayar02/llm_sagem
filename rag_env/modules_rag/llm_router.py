#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm_router.py — Compteur de tokens + bascule automatique entre LLMs
========================================================================

SCAFFOLD — squelette à compléter, non exécuté ici.

Objectif (point 6 du mail) : optimiser la consommation des tokens gratuits de
chaque fournisseur en basculant automatiquement au suivant quand le quota
gratuit du mois est épuisé, plutôt que de payer ou de tomber en erreur.

Limites connues à garder en tête :
  - Chaque fournisseur a son propre tokenizer. `tiktoken` est fiable pour les
    modèles OpenAI mais donne seulement une ESTIMATION pour Claude (Anthropic
    ne publie pas de tokenizer public identique). Pour un comptage exact côté
    Claude, utiliser `client.messages.count_tokens(...)` de l'API Anthropic
    plutôt que tiktoken.
  - Les "quotas gratuits" ne sont pas interrogeables par API chez la plupart
    des fournisseurs : ce module les traque donc localement (compteur maison,
    fichier JSON ou base légère) plutôt que de les lire depuis une API de
    facturation.
"""

import os
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

USAGE_FILE = Path(os.getenv("LLM_USAGE_FILE", "./llm_usage.json"))

FALLBACK_ORDER = [p.strip() for p in os.getenv("LLM_FALLBACK_ORDER", "anthropic,openai,ollama").split(",") if p.strip()]

FREE_QUOTAS = {
    "anthropic": int(os.getenv("ANTHROPIC_FREE_TOKEN_QUOTA", "0")),
    "openai": int(os.getenv("OPENAI_FREE_TOKEN_QUOTA", "0")),
    "xai": int(os.getenv("XAI_FREE_TOKEN_QUOTA", "0")),
    "ollama": float("inf"),  # local = pas de quota, juste le coût matériel
}


@dataclass
class UsageRecord:
    provider: str
    tokens_used: int = 0
    month: str = ""  # format "2026-08"


def _current_month() -> str:
    return time.strftime("%Y-%m")


def _load_usage() -> dict:
    if USAGE_FILE.exists():
        return json.loads(USAGE_FILE.read_text(encoding="utf-8"))
    return {}


def _save_usage(usage: dict):
    USAGE_FILE.write_text(json.dumps(usage, indent=2, ensure_ascii=False), encoding="utf-8")


def record_usage(provider: str, tokens: int):
    usage = _load_usage()
    month = _current_month()
    key = f"{provider}:{month}"
    usage[key] = usage.get(key, 0) + tokens
    _save_usage(usage)


def tokens_remaining(provider: str) -> float:
    usage = _load_usage()
    used = usage.get(f"{provider}:{_current_month()}", 0)
    quota = FREE_QUOTAS.get(provider, 0)
    if quota == float("inf"):
        return float("inf")
    return max(0, quota - used)


def count_tokens(text: str, provider: str = "anthropic") -> int:
    """Estimation du nombre de tokens. Pour un comptage EXACT côté Claude,
    préférer client.messages.count_tokens() de l'API Anthropic avant un appel
    critique (ingestion en masse par ex.), tiktoken n'étant qu'une approximation."""
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def pick_provider(estimated_tokens: int) -> str:
    """Retourne le premier fournisseur de FALLBACK_ORDER qui a assez de tokens
    gratuits restants ce mois-ci. Retombe sur 'ollama' (local, illimité) si
    tous les quotas API sont épuisés et qu'Ollama est configuré."""
    for provider in FALLBACK_ORDER:
        if tokens_remaining(provider) >= estimated_tokens:
            return provider
    return "ollama"


def call_llm(system_prompt: str, user_prompt: str, provider: Optional[str] = None) -> str:
    """
    Point d'entrée unique pour le reste du code (rag_extractor.py, agents/).
    Si `provider` n'est pas précisé, choisit automatiquement selon les quotas.

    TODO : brancher les vrais clients SDK (anthropic.Anthropic(), openai.OpenAI(),
    requête HTTP pour xAI/Grok, requests vers OLLAMA_BASE_URL pour Ollama) —
    squelette volontairement laissé en NotImplementedError pour éviter tout
    appel réel avant validation du choix de fournisseur et du budget.
    """
    estimated = count_tokens(system_prompt + user_prompt)
    chosen = provider or pick_provider(estimated)

    if chosen == "anthropic":
        raise NotImplementedError(
            "Brancher anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY')).messages.create(...)"
        )
    elif chosen == "openai":
        raise NotImplementedError("Brancher openai.OpenAI().chat.completions.create(...)")
    elif chosen == "xai":
        raise NotImplementedError("Brancher l'appel HTTP vers l'API xAI (Grok)")
    elif chosen == "ollama":
        import requests
        resp = requests.post(
            f"{os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}/api/generate",
            json={
                "model": os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
                "prompt": f"{system_prompt}\n\n{user_prompt}",
                "stream": False,
                "options": {"num_ctx": 8192, "temperature": 0, "num_predict": 4096},
            },
            timeout=600,
        )
        resp.raise_for_status()
        return resp.json()["response"]
    else:
        raise ValueError(f"Fournisseur inconnu : {chosen}")


if __name__ == "__main__":
    for p in FALLBACK_ORDER + ["ollama"]:
        print(f"{p:10s} -> quota restant estimé : {tokens_remaining(p)}")
