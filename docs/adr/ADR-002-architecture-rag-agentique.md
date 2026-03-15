# ADR-002 : Architecture 100% RAG agentique vs alternatives

**Statut** : Accepté  
**Date** : 2025  
**Décideurs** : Équipe technique  

---

## Contexte

Le chatbot doit répondre à des questions sur un domaine d'expertise exigeant (cafés de spécialité, origines, torréfactions, boutiques parisiennes), avec une forte contrainte de fiabilité : aucune information inventée ne doit atteindre l'utilisateur.

Trois architectures ont été évaluées :

1. **Fine-tuning** : entraînement d'un modèle sur les données L'Arbre à Café
2. **RAG classique** : retrieval + LLM, prompt statique, pas de sélection d'outils
3. **RAG agentique** : retrieval via outils spécialisés + orchestration multi-étapes

---

## Décision

**Architecture 100% RAG agentique** avec 6 outils spécialisés et orchestration sur mesure.

Flux :
```
Query → Planning (GPT-4o-mini, T=0.3) → Sélection outils (max 3) → Exécution RAG/KB 
→ Contexte récupéré → Génération (GPT-4o-mini, T=0.1) → Validation 5 couches → Réponse
```

---

## Justifications

| Critère | Fine-tuning | RAG classique | RAG agentique |
|---|---|---|---|
| Fraîcheur des données | Stale (re-training) | Dynamique | Dynamique |
| Coût de mise à jour KB | Très élevé | Scrape + rebuild | Scrape + rebuild |
| Risque hallucination | Élevé (paramétrique) | Moyen | Faible (5-layer guard) |
| Précision basse température | Limitée | Bonne | Excellente |
| Décomposition multi-étapes | Non | Non | Oui |
| Interprétation d'intention | Figée | Limitée | Flexible |

La nature du domaine (données structurées : horaires, adresses, prix, origines) se prête idéalement à la recherche dirigée par outils plutôt qu'à la génération paramétrique.

Les 6 outils correspondent à des intentions client distinctes et prévisibles :
`search_knowledge`, `get_boutiques`, `get_boutique_info`, `get_contact`, `get_hours`, `find_nearest_boutique`.

---

## Conséquences

- **Positives** : Zéro donnée codée en dur dans les prompts. Mise à jour automatique par scraping (scraper → KB → FAISS → propagation). Réponses ancrées dans le contexte récupéré.
- **Négatives** : 2 appels LLM par requête (planning + génération) → latence ~1–3s (LLM). Complexité d'orchestration supérieure à un RAG classique.
- **Décision clé** : Température de planning à 0.3 (diversité de sélection d'outils) vs température de génération à 0.1 (cohérence de la réponse finale). Voir ADR-004.
