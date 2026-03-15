# ADR-005 : Source de vérité unique — KB JSON canonique

**Statut** : Accepté  
**Date** : 2025  
**Décideurs** : Équipe technique  

---

## Contexte

Un chatbot qui maintient des données à plusieurs endroits (base SQL, prompts système, fichiers de config, code hardcodé) court un risque élevé d'incohérences : une boutique mise à jour dans la DB mais pas dans le prompt, un horaire écrit en dur dans le code qui contredit la réalité.

La décision porte sur : où vit la vérité des données (boutiques, horaires, produits, liens) ?

---

## Décision

**Une seule source de vérité** : `larbrecaf_knowledge_industrial_2025.json` (v4.0_industrial).

Règles absolues :
- Zéro donnée codée en dur dans `ai_agent.py`, `knowledge_base_enriched.py` ou les prompts système
- Toutes les données métier (adresses, téléphones, horaires, produits, URLs) proviennent de la KB
- Les règles de routing d'outils (ex: mapping département → ville) sont générées dynamiquement depuis la KB via `get_department_mapping()`
- Les exemples dans le prompt de planning sont auto-générés depuis la KB via les 4 premières boutiques

---

## Flux de mise à jour

```
larbreacafe.com (site officiel)
       ↓ scraper_industrial_2025.py (JSON-LD + HTML parser)
larbrecaf_knowledge_industrial_2025.json  ← SEULE source de vérité
       ↓ RAGEngine._build_or_load_index()
FAISS IndexFlatL2 (+ embeddings_cache.pkl)
       ↓ EnrichedKnowledgeBase.search()
AIAgent (6 outils) → Réponse utilisateur
```

Aucun changement de code n'est nécessaire lors d'une mise à jour de données : seul le scraper s'exécute.

---

## Alternatives écartées

- **Base de données SQL** : surcoût opérationnel (migrations, ORM, connexion), inadapté à un corpus de documents texte.
- **Données dans le prompt système** : impossible à maintenir, dépasse rapidement la fenêtre de contexte, viole le principe RAG.
- **Plusieurs fichiers JSON** : risque de désynchronisation entre fichiers, complexité de réconciliation.

---

## Conséquences

- **Positives** : Propagation automatique de toute modification du site web en production (scraping → KB → FAISS). Pas de maintenance du code pour les mises à jour de données. Cohérence garantie.
- **Négatives** : Le scraper est un point de défaillance critique. Si le format HTML de larbreacafe.com change, le scraper doit être mis à jour.
- **Monitoring** : La date de dernière mise à jour est stockée dans la KB (`date_scraping`). À monitorer pour détecter une inactivité anormale du CI/CD.
