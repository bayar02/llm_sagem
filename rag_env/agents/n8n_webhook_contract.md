# Contrat webhook n8n — Envoi du rapport final ICP → MTP par email

Ce document décrit le contrat d'échange entre l'application (ou l'agent
`reporting_agent` de `crew_agents.py`) et un workflow n8n chargé d'envoyer le
rapport final de conformité par email.

## 1. Vue d'ensemble

```
[app.py / ReportingAgent] --POST webhook--> [n8n workflow] --SMTP/Email node--> [destinataires]
```

n8n reste responsable de :
- la mise en forme finale de l'email (template HTML n8n),
- la gestion des destinataires (liste, CC),
- l'éventuel archivage (ex. écriture dans Google Drive / SharePoint avant l'envoi),
- les retries en cas d'échec d'envoi.

L'application reste responsable de :
- produire le rapport (JSON structuré + pièce jointe si besoin),
- appeler le webhook une seule fois par rapport généré (idempotence côté n8n
  recommandée via `report_id`).

## 2. Requête (app -> n8n)

`POST {N8N_WEBHOOK_URL}`

Headers :
```
Content-Type: application/json
Authorization: Bearer {N8N_WEBHOOK_TOKEN}
```

Corps (exemple) :
```json
{
  "report_id": "DIW377_ALTICE_20260818_1",
  "product": "DIW377_ALTICE",
  "generated_at": "2026-08-18T14:32:00+01:00",
  "summary": {
    "total_tests": 42,
    "pass": 39,
    "fail": 2,
    "na": 1
  },
  "anomalies": [
    {"severity": "CRITICAL", "test": "PT12", "message": "Power hors limite ICP (mesuré 21.4 dBm, limite max 20 dBm)"}
  ],
  "recommendations": [
    "Vérifier l'étalonnage RF sur la chaîne 2.4GHz avant la prochaine série."
  ],
  "report_url": "https://.../rapport_DIW377_ALTICE_20260818.pdf",
  "recipients": ["destinataire1@exemple.com", "destinataire2@exemple.com"]
}
```

Champs :

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `report_id` | string | oui | Identifiant unique du rapport (idempotence) |
| `product` | string | oui | Identifiant produit |
| `generated_at` | string ISO 8601 | oui | Horodatage de génération |
| `summary` | object | oui | Compteurs agrégés PASS/FAIL/N-A |
| `anomalies` | array | non | Liste des anomalies détectées (CRITICAL/WARNING/INFO) |
| `recommendations` | array | non | Recommandations actionnables |
| `report_url` | string | non | Lien vers le rapport complet (PDF/Excel) si hébergé |
| `recipients` | array | non | Si absent, n8n utilise une liste par défaut configurée dans le workflow |

## 3. Réponse (n8n -> app)

```json
{"status": "ok", "email_sent": true, "message_id": "..."}
```

En cas d'erreur, n8n doit répondre avec un code HTTP ≥ 400 et un corps
`{"status": "error", "reason": "..."}` pour que `reporting_agent` puisse logguer
l'échec et éventuellement réessayer.

## 4. Points à valider avec l'équipe avant implémentation

- [ ] Confirmer l'outil d'envoi (SMTP interne ? Gmail/Outlook via n8n node natif ?)
- [ ] Confirmer la liste des destinataires par défaut (peut varier par produit/client)
- [ ] Décider si le PDF complet est joint à l'email ou seulement lié (taille des pièces jointes)
- [ ] Sécuriser le webhook (token statique suffisant, ou passer par une authentification plus forte si n8n est exposé publiquement)
