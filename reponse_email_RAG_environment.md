Objet : Re: Proposition d'étapes — environnement RAG / Agentic IA

Bonjour,

Merci pour ce plan, il est clair et couvre bien l'ensemble des briques
nécessaires. Je propose de le reprendre en le séquençant par priorité, avec
un environnement de base (scaffold) déjà prêt pour démarrer sans attendre
que tous les choix soient tranchés.

**Constat de départ** : `mtp_analyzer.py` montre qu'une première tentative
d'analyse par Claude API avait été faite puis remplacée par du parsing
classique ("Analyse par code classique (sans IA)"). Je pars du principe que
cette bascule était liée au coût/à la fiabilité des appels IA sans filet de
sécurité — c'est justement ce que la gestion des tokens (point 6) et une
stratégie de validation en parallèle (RAG vs extraction classique existante)
doivent corriger avant qu'on ne réintroduise l'IA en production.

**Proposition de phasage :**

*Phase 1 — Socle technique (semaine 1-2)*
Choix du LLM (je pars sur l'API Claude pour démarrer, cohérent avec les
prompts déjà écrits dans `mtp_analyzer.py`), installation de Qdrant (via
Docker), mise en place du compteur de tokens et du routeur multi-LLM
(bascule automatique selon quotas gratuits). Un scaffold complet (docker-compose,
requirements, modules squelettes) est déjà prêt côté environnement, à
brancher aux vraies clés API.

*Phase 2 — RAG sur les documents produits (semaine 2-4)*
Chunking + embedding + indexation des PDFs ICP/MTP, recherche hybride
(vecteur + mots-clés, utile pour les identifiants exacts type "PT12" ou
"Test#7"). Traitement des images : je propose de commencer par de l'OCR
classique (pytesseract) plutôt que YOLO, à valider une fois qu'on aura
confirmé si les tableaux de limites sont vraiment en image ou déjà en texte
sélectionnable dans les PDFs.

*Phase 3 — Validation avant bascule (semaine 4-5)*
Extraction RAG exécutée en parallèle de `icp_fe_extract.py` (regex classique
existant) sur les 5 produits déjà disponibles (ALTICE, DCIW378, DISH, LOWI,
VF_PT), comparaison des JSON produits. On ne bascule en production que si
l'écart est nul ou expliqué — le code classique reste en filet de sécurité.

*Phase 4 — Agentic IA et automatisation (semaine 5-7)*
Orchestration CrewAI (agents ingestion / extraction / comparaison /
reporting) + webhook n8n pour l'envoi automatique du rapport final ICP→MTP
par email. Contrat d'échange déjà rédigé pour cadrer cette intégration.

**Points à trancher avec vous avant de lancer la Phase 1 :**
1. Budget/accès API à prévoir (Claude en priorité, avec quel plafond mensuel) ?
2. Qdrant ou Weaviate — je recommande Qdrant (plus léger, hybrid search
   natif), sauf contrainte particulière de votre côté ?
3. CrewAI et n8n en parallèle, ou n8n seulement une fois CrewAI validé ?
4. Microsoft Fabric : je le mets en recherche complémentaire hors chemin
   critique, sauf si c'est déjà une direction actée côté équipe/IT ?
5. Échéance visée pour une première démo (même partielle) ?

Je vous tiens au courant dès que la Phase 1 est opérationnelle.

Bien cordialement,
