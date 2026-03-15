# ADR-001 : FAISS local vs base vectorielle managée

**Statut** : Accepté  
**Date** : 2025  
**Décideurs** : Équipe technique  

---

## Contexte

Le moteur RAG nécessite un index vectoriel pour réaliser la recherche sémantique sur la base de connaissance.  
Deux grandes familles de solutions ont été évaluées :

- **Services vectoriels managés** : Pinecone, Weaviate, Qdrant Cloud, ChromaDB Cloud
- **Index local** : FAISS (Facebook AI Similarity Search), open-source, embarqué dans le processus Python

Le volume de données à indexer est maîtrisé : ~98 pages scrapées + 5 boutiques = quelques centaines de documents.

---

## Décision

**FAISS local** (`faiss-cpu`, `IndexFlatL2`) est retenu comme moteur de recherche vectorielle.

---

## Justifications

| Critère | FAISS local | Service managé |
|---|---|---|
| Coût infrastructure | 0€ | 70–200€/mois (usage réel) |
| Latence | <10ms (même processus) | 50–200ms (réseau) |
| Dépendances externes | Aucune | Clé API + réseau + SLA tiers |
| Contrôle des données | Total (données L'Arbre à Café) | Données envoyées vers cloud |
| Complexité opérationnelle | Faible (fichier cache pkl) | Élevée (gestion du cluster) |
| Scalabilité nécessaire | Faible (KB stable, ~98 pages) | Pertinente à grande échelle |

La taille de la base de connaissance (corpus de taille fixe, pas de millions de documents) rend inutile la scalabilité distribuée d'un service cloud.

Le cache d'embeddings (`embeddings_cache.pkl`, keyed par MD5 du contenu) évite les appels répétés à l'API OpenAI lors des redémarrages.

---

## Conséquences

- **Positives** : Coût d'infrastructure = 0€. Latence sub-10ms. Aucune dépendance réseau supplémentaire.
- **Négatives** : Rebuild manuel de l'index si le volume de données dépasse ~100 000 documents (non anticipé). L'index est non persisté entre redémarrages sans le cache pkl.
- **Risques résiduels** : Si la variable `REBUILD_EMBEDDINGS=true` est activée accidentellement en production, un cold-start complet via l'API OpenAI sera déclenché (~30s). Mitigation : valeur par défaut `false`.
