# ADR-006 : Orchestration agentique sur mesure vs frameworks existants

**Statut** : Accepté  
**Date** : 2025  
**Décideurs** : Équipe technique  

---

## Contexte

L'orchestration multi-outils peut être déléguée à un framework (LangChain, LlamaIndex, CrewAI, AutoGen) ou implémentée sur mesure.  

Le projet requiert :
- Sélection dynamique de 1 à 3 outils par requête
- Paramétrage contextuel des outils (ville extraite de la requête)
- Mémoire de conversation sur 10 messages
- Contrôle fin sur les erreurs LLM (fallback sur `search_knowledge`)
- 5 couches de validation post-génération custom

---

## Décision

**Orchestration sur mesure** implémentée dans `AIAgent` (`plan_and_execute()` + `execute_tool()` + `_validate_response()`), sans framework tiers.

---

## Justifications

| Critère | Framework (LangChain etc.) | Sur mesure |
|---|---|---|
| Dépendances | Lourdes (>50 deps transitives) | Minimales (openai, faiss, requests) |
| Surface d'attaque sécurité | Large | Maîtrisée |
| Contrôle du prompt de planning | Partiel (abstraction) | Total |
| Contrôle de la validation | Difficile à hooker | Native |
| Debug et observabilité | Complexe (chaînes abstraites) | Direct (logs JSON structurés) |
| Compatibilité Python 3.12 | Risque de breaking changes | Stable |
| Courbe d'apprentissage équipe | Élevée | Faible |

La logique d'orchestration du projet tient en ~80 lignes (`plan_and_execute`). L'ajout d'un framework pour 80 lignes constituerait de la sur-ingénierie.

**Séquencement explicite** : le planning (GPT-4o-mini T=0.3) produit un JSON `{"tools_to_use": [...]}` déterministe. Chaque outil est appelé séquentiellement, les résultats sont concaténés. C'est intentionnellement simple et lisible.

**Fallback robuste** : toute exception dans `plan_and_execute` se rabat sur `search_knowledge(user_query)` directement. Aucun framework ne gère ce cas aussi simplement.

---

## Conséquences

- **Positives** : Code minimal et lisible. Débogage facilité par le logger JSON structuré. Aucune breaking change de framework en production.
- **Négatives** : Fonctionnalités avancées (retry automatique, parallel tool calls, streaming) doivent être implémentées manuellement si besoin.
- **Évolutivité** : Ajout d'un 7e outil = 1 entrée dans `_define_tools()` + 1 `elif` dans `execute_tool()`. Coût de maintenance faible.
