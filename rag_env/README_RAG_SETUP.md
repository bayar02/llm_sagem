# Guide d'installation — Environnement RAG / Agentic IA (telecom_validator)

Ce guide accompagne le scaffold `rag_env/` livré à côté du projet
`telecom_validator`. Il correspond aux points 1 à 4 et 6 du mail reçu
(choix du LLM, base vectorielle, concepts RAG, agentic IA, gestion des tokens).

**Important — portée de cette livraison** : ce dossier est un **scaffold**
(squelettes de code + config), pas un pipeline exécuté. Aucun traitement n'a
été lancé sur vos PDFs réels. Chaque module contient des `TODO` et parfois des
`NotImplementedError` à l'endroit précis où un choix (fournisseur LLM,
stratégie OCR, etc.) doit être branché.

---

## 0. Constat de départ (pour situer le besoin)

Le projet `telecom_validator` a **déjà exploré la voie IA** : `mtp_analyzer.py`
contient encore les prompts d'une version "analyse par Claude API", mais le
code a été **repassé en extraction classique par regex/parsing**
(`# Analyse par code classique (sans IA)`). C'est le signe que la première
tentative IA n'avait probablement pas la robustesse ou le contrôle de coût
nécessaires pour rester en production — exactement ce que ce plan (RAG +
routeur multi-LLM + agents) vise à corriger avant de réintroduire l'IA.

`icp_fe_extract.py` documente lui aussi des correctifs réguliers pour
absorber les variations de mise en page entre produits (DIW377, DCIW378,
DIW253...) — un bon candidat pour être complété (pas nécessairement remplacé)
par une extraction RAG plus tolérante aux variations, avec le regex classique
gardé comme filet de sécurité.

---

## 1. Choix du LLM

| Option | Quand la choisir |
|---|---|
| **Ollama (local)** | Poste avec GPU correct (≥ 8 Go VRAM recommandé pour un modèle 7-8B correct type Llama 3.1 8B ou Mistral). Aucun coût par appel, mais latence et qualité dépendent du matériel. |
| **API (Claude / GPT / Grok)** | Meilleure qualité immédiate, coût à l'usage. Le projet a déjà des prompts pensés pour Claude (`mtp_analyzer.py`) — c'est l'option la plus cohérente pour redémarrer. |

**Installation Ollama (Windows)** :
1. Télécharger l'installeur depuis https://ollama.com/download/windows
2. Lancer l'installeur (ajoute `ollama` au PATH et démarre un service local sur `http://localhost:11434`)
3. Récupérer un modèle : `ollama pull llama3.1:8b` (ou `mistral`, `qwen2.5:7b`)
4. Tester : `ollama run llama3.1:8b "Bonjour"`
5. Renseigner `OLLAMA_BASE_URL` / `OLLAMA_MODEL` dans `.env`

**API** : créer les clés sur les consoles respectives et les mettre dans `.env`
(voir `.env.example`). `llm_router.py` gère la bascule entre plusieurs
fournisseurs selon les quotas gratuits restants (point 6 du mail).

---

## 2. Base de données vectorielle

Qdrant est recommandé (voir justification dans `docker/docker-compose.yml`) :

```bash
cd rag_env/docker
docker compose up -d
# Dashboard : http://localhost:6333/dashboard
```

Alternative sans Docker pour un premier test rapide : `QdrantClient(path="./qdrant_local_data")`
en mode fichier local (à adapter dans `retriever.py` / `ingest.py`).

Weaviate reste possible (service alternatif commenté dans le `docker-compose.yml`)
si vous préférez ses modules de vectorisation intégrés — mais ajoute de la
complexité de déploiement pour un bénéfice marginal ici, vu que l'embedding
est de toute façon calculé côté Python (Voyage AI ou local).

---

## 3. Concepts clés (pense-bête)

- **Chunking** : découper les PDFs en morceaux (≈ 500-1000 caractères, avec
  chevauchement ~150) pour que chaque passage envoyé au LLM tienne dans le
  contexte et reste pertinent. Voir `modules_rag/ingest.py::chunk_text`.
- **Embedding** : représentation vectorielle d'un texte, utilisée pour la
  recherche par similarité. Claude n'a pas d'endpoint d'embedding natif —
  Voyage AI est le fournisseur recommandé par Anthropic pour ça (fallback
  local possible avec `sentence-transformers` / BGE, gratuit mais moins
  précis et plus lent sans GPU).
- **Indexation** : stocker les vecteurs + métadonnées (produit, page, PDF
  source) dans Qdrant pour pouvoir les rechercher ensuite.
- **Hybrid search** : combiner recherche vectorielle (sens) et recherche
  lexicale/BM25 (mots-clés exacts type "PT12", "Test#7") — important ici car
  les documents produits contiennent beaucoup d'identifiants exacts que la
  seule recherche sémantique retrouve mal. Voir `modules_rag/retriever.py`.
- **Tokens** : unité de facturation/quota des LLMs. Le comptage exact varie
  par fournisseur — `llm_router.py` utilise une estimation (`tiktoken`) plus
  un compteur d'usage local par mois, faute d'API de quota universelle.

---

## 4. RAG appliqué aux PDFs produits (ICP / MTP)

Étapes prévues (voir `modules_rag/ingest.py` et `modules_rag/rag_extractor.py`) :

1. Extraction du texte par page (réutilise `fitz`/PyMuPDF, déjà présent dans le projet)
2. Traitement des images/tableaux scannés (voir section 5 ci-dessous)
3. Chunking + embedding + indexation dans Qdrant, avec le produit en métadonnée
   (permet de filtrer la recherche par produit, ex. `DIW377_ALTICE`)
4. Recherche hybride pour ne récupérer que les passages pertinents avant
   d'appeler le LLM (économie de tokens vs envoyer le PDF entier)
5. Extraction structurée par le LLM avec un contrat JSON strict, identique à
   celui déjà produit par `icp_fe_extract.py`, pour rester compatible avec le
   reste de l'application sans rien changer côté validation des logs

**Stratégie de mise en production recommandée** : faire tourner l'extraction
RAG en parallèle de l'extraction classique sur les PDFs déjà présents dans
`LOGS_*` (5 produits disponibles : ALTICE, DCIW378, DISH, LOWI, VF_PT), comparer
les JSON produits, et ne basculer que lorsque l'écart est nul ou expliqué.
Ce test comparatif n'a pas été exécuté dans cette livraison (scaffold only) —
c'est la première chose à lancer une fois l'environnement installé.

---

## 5. Traitement des images dans les PDFs (OCR vs YOLO)

Deux approches possibles, décrites dans `modules_rag/ingest.py::traiter_images_page` :

- **OCR (pytesseract + pdf2image)** — à essayer en premier. Bon pour du texte
  scanné en image (tableaux de limites non sélectionnables). Nécessite
  d'installer les binaires natifs :
  - Windows : Tesseract (https://github.com/UB-Mannheim/tesseract/wiki) +
    Poppler pour Windows (https://github.com/oschwartz10612/poppler-windows) —
    ajouter les deux au PATH.
- **YOLO (détection d'objets)** — à réserver si le besoin est de repérer/classer
  des schémas ou captures d'écran spécifiques plutôt que d'en extraire du
  texte. Nécessite un modèle entraîné/fine-tuné sur vos documents, donc un
  investissement plus lourd — ne pas commencer par là.

Recommandation : valider d'abord si les PDFs ICP/MTP contiennent réellement du
texte "en image" non sélectionnable (à vérifier avec `pdfplumber`/`fitz` — si
`page.get_text()` renvoie déjà le contenu, l'OCR n'est même pas nécessaire).

---

## 6. Gestion des tokens et bascule multi-LLM

Voir `modules_rag/llm_router.py`. Principe :
- un compteur d'usage local par fournisseur et par mois (`llm_usage.json`)
- un ordre de préférence configurable (`LLM_FALLBACK_ORDER` dans `.env`)
- bascule automatique vers le fournisseur suivant quand le quota gratuit
  configuré est atteint, avec Ollama local comme filet ultime (illimité mais
  dépendant du matériel)

À faire avant mise en service : renseigner les vrais montants de quota
gratuit dans `.env` (ils varient et changent régulièrement selon les offres
de chaque fournisseur — à vérifier sur leurs consoles respectives plutôt que
de se fier à une valeur figée ici).

---

## 7. Agentic IA et automatisation (CrewAI / n8n)

- `agents/crew_agents.py` : squelette de 4 agents CrewAI (ingestion,
  extraction, comparaison, reporting) calqués sur le workflow déjà documenté
  dans le `README.md` de `telecom_validator`.
- `agents/n8n_webhook_contract.md` : contrat d'échange proposé entre
  l'application et un workflow n8n pour l'envoi du rapport final par email.

n8n lui-même n'est pas installé par ce scaffold (c'est un outil séparé,
généralement déployé via Docker ou en SaaS) — le contrat webhook est prêt à
être branché une fois l'instance n8n disponible.

---

## 8. Microsoft Fabric — pistes de recherche complémentaire

Non creusé dans cette livraison (hors scope du scaffold technique), mais à
investiguer séparément si l'équipe veut évaluer Fabric comme alternative/complément
à Qdrant + scripts Python pour l'ingestion et le reporting :
- Lakehouse Fabric comme entrepôt central pour les rapports ICP/MTP structurés
  (au lieu d'exports JSON/Excel dispersés)
- Power BI intégré pour le reporting final (point 7 du mail) — alternative ou
  complément à l'envoi par email via n8n
- Coût et gouvernance : Fabric est un engagement Microsoft/Azure plus lourd
  que Qdrant + Python — à ne considérer que si l'équipe est déjà dans
  l'écosystème Microsoft 365/Azure.

---

## 9. Ordre d'installation recommandé

```bash
# 1. Dépendances Python
pip install -r requirements.txt -r rag_env/requirements_rag.txt

# 2. Config
cp rag_env/.env.example rag_env/.env
# éditer rag_env/.env avec vos clés API réelles

# 3. Qdrant
cd rag_env/docker && docker compose up -d && cd ../..

# 4. (si Ollama retenu) installer Ollama + pull un modèle (voir section 1)

# 5. (si OCR retenu) installer Tesseract + Poppler (voir section 5)

# 6. Premier test d'ingestion sur UN produit déjà connu
python rag_env/modules_rag/ingest.py --pdf "chemin/vers/ICP_PRODUCT_ALTICE_DIW377_v1.4.pdf" --product DIW377_ALTICE

# 7. Test de recherche
python rag_env/modules_rag/retriever.py "limite de puissance RF 5GHz"

# 8. Comparaison extraction RAG vs classique (une fois llm_router.py branché à un vrai SDK)
python rag_env/modules_rag/rag_extractor.py "chemin/vers/ICP_....pdf" DIW377_ALTICE
```

Les étapes 6 à 8 nécessitent d'abord de compléter les `NotImplementedError`
dans `llm_router.py::call_llm` avec le SDK du fournisseur choisi.
