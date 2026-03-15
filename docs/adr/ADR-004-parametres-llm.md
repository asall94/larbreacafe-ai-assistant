# ADR-004 : Paramètres LLM — Modèle et températures différenciées

**Statut** : Accepté  
**Date** : 2025  
**Décideurs** : Équipe technique  

---

## Contexte

Deux appels LLM distincts sont réalisés par requête :
1. **Planning** : sélection des outils à utiliser et de leurs paramètres (ex: quelle ville passer à `get_boutique_info`)
2. **Génération** : synthèse d'une réponse naturelle depuis le contexte RAG récupéré

Ces deux tâches ont des profils différents : la sélection d'outils nécessite une certaine flexibilité d'interprétation, la génération de réponse exige une précision maximale.

---

## Décision

| Appel | Modèle | Température | max_tokens |
|---|---|---|---|
| Planning (sélection outils) | `gpt-4o-mini` | 0.3 | 300 |
| Génération (réponse finale) | `gpt-4o-mini` | 0.1 | 500 |
| Embeddings | `text-embedding-ada-002` | — | — |

---

## Justifications

**Choix du modèle : `gpt-4o-mini`**  
- Rapport performance/coût optimal pour les tâches de classification d'intention et de synthèse de texte structuré.  
- Latence inférieure à GPT-4o (~1–2s vs ~3–5s) sans dégradation mesurable sur ce domaine.  
- Fiable pour suivre des instructions JSON strictes (output de planning).

**Températures différenciées**  
- `T=0.1` pour la génération : minimise la variabilité et les inventions dans les réponses finales. L'information vient du contexte RAG, pas de la créativité du modèle.  
- `T=0.3` pour le planning : permet une sélection d'outils légèrement moins rigide, gérant mieux les requêtes ambiguës où plusieurs outils sont pertinents.  
- `T=0.0` (déterministe pur) a été écarté pour le planning car il bloquait sur certaines requêtes multi-intentions.

**Embeddings : `text-embedding-ada-002`**  
- Dimension 1536, compatible FAISS `IndexFlatL2` directement.  
- Stable, API mature, coût bas.  
- Batch size de 20 pour respecter les limites de l'API OpenAI.

---

## Conséquences

- **Positives** : Réponses cohérentes et précises (T=0.1). Flexibilité de planning suffisante (T=0.3). Coût maîtrisé (gpt-4o-mini).
- **Négatives** : Dépendance à l'API OpenAI pour embeddings ET génération. Risque de coupure si quota dépassé.
- **Mitigation** : Cache d'embeddings par hash MD5 → les embeddings ne sont recalculés qu'en cas de changement de la KB.
