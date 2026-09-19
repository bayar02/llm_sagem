#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crew_agents.py — Orchestration multi-agents (CrewAI) pour le pipeline ICP -> MTP
====================================================================================

SCAFFOLD — définitions d'agents et de tâches, non exécuté ici.

Objectif (points 4 et 7 du mail) : automatiser la chaîne complète
  ingestion -> extraction -> comparaison ICP/MTP -> rapport -> envoi mail,
  en utilisant CrewAI pour orchestrer les étapes et n8n pour le déclenchement
  externe / la livraison (webhook -> email).

Découpage en 4 agents, calqué sur le "Workflow en 7 étapes" déjà documenté
dans le README de telecom_validator (parties ICP et MTP) :

  1. IngestionAgent   : ingère les PDFs (ICP + MTP) dans Qdrant (ingest.py)
  2. ExtractionAgent  : extrait les limites/résultats structurés (rag_extractor.py
                         + mtp_extractor.py existant)
  3. ComparisonAgent  : compare ICP vs MTP, détecte les anomalies
                         (réutilise compare_mtp_vs_icp existant si possible)
  4. ReportingAgent   : génère le rapport final et déclenche le webhook n8n
                         (voir n8n_webhook_contract.md)

Ce fichier est un squelette : les `Agent`/`Task`/`Crew` de CrewAI sont
instanciés mais les `tools` réels (fonctions Python à exposer aux agents) sont
à brancher une fois les modules ci-dessus validés individuellement.
"""

import os
from dotenv import load_dotenv

load_dotenv()

try:
    from crewai import Agent, Task, Crew, Process
except ImportError:
    raise SystemExit("crewai non installé — pip install -r requirements_rag.txt")


# ─────────────────────────────────────────────────────────────
# Agents
# ─────────────────────────────────────────────────────────────

ingestion_agent = Agent(
    role="Agent d'ingestion documentaire",
    goal="Ingérer les PDFs ICP et MTP d'un produit dans la base vectorielle Qdrant",
    backstory=(
        "Spécialiste du traitement documentaire télécom, tu prépares les documents "
        "pour que les autres agents puissent y chercher de l'information précise."
    ),
    verbose=True,
    # tools=[...]  # TODO : brancher ingest.py comme outil CrewAI (@tool)
)

extraction_agent = Agent(
    role="Agent d'extraction technique",
    goal="Extraire les limites ICP (FE, RF, BT) et les résultats MTP sous forme structurée",
    backstory=(
        "Expert des formats de test PEGATRON/Sagemcom, tu structures les données "
        "brutes des documents en JSON exploitable, avec repli vers l'extraction "
        "classique (regex) en cas de doute."
    ),
    verbose=True,
    # tools=[...]  # TODO : brancher rag_extractor.py + mtp_extractor.py
)

comparison_agent = Agent(
    role="Agent de comparaison de conformité",
    goal="Comparer les spécifications ICP et les résultats MTP, détecter les anomalies",
    backstory="Auditeur qualité, tu vérifies la correspondance test par test et signales les écarts.",
    verbose=True,
    # tools=[...]  # TODO : brancher compare_mtp_vs_icp existant (modules/mtp_extractor.py)
)

reporting_agent = Agent(
    role="Agent de reporting",
    goal="Générer le rapport final de conformité et déclencher son envoi par email via n8n",
    backstory="Tu produis un rapport clair et déclenches la notification finale à l'équipe.",
    verbose=True,
    # tools=[...]  # TODO : brancher un appel HTTP vers N8N_WEBHOOK_URL (voir .env.example)
)


def build_crew(product: str, icp_pdf: str, mtp_pdf: str) -> Crew:
    task_ingest = Task(
        description=f"Ingérer les PDFs ICP ({icp_pdf}) et MTP ({mtp_pdf}) du produit {product} dans Qdrant.",
        expected_output="Confirmation du nombre de chunks indexés par document.",
        agent=ingestion_agent,
    )

    task_extract = Task(
        description=f"Extraire les limites ICP et les résultats MTP structurés pour {product}.",
        expected_output="Deux objets JSON : ICP_Limits et MTP_Results.",
        agent=extraction_agent,
        context=[task_ingest],
    )

    task_compare = Task(
        description="Comparer ICP_Limits et MTP_Results, lister les anomalies CRITICAL/WARNING/INFO.",
        expected_output="JSON de comparaison avec anomalies et recommandations.",
        agent=comparison_agent,
        context=[task_extract],
    )

    task_report = Task(
        description="Générer le rapport final de conformité et l'envoyer via le webhook n8n configuré.",
        expected_output="Confirmation d'envoi (statut HTTP du webhook n8n) + lien/chemin du rapport.",
        agent=reporting_agent,
        context=[task_compare],
    )

    return Crew(
        agents=[ingestion_agent, extraction_agent, comparison_agent, reporting_agent],
        tasks=[task_ingest, task_extract, task_compare, task_report],
        process=Process.sequential,
        verbose=True,
    )


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: python crew_agents.py <product> <icp_pdf> <mtp_pdf>")
        sys.exit(1)
    crew = build_crew(sys.argv[1], sys.argv[2], sys.argv[3])
    result = crew.kickoff()
    print(result)
