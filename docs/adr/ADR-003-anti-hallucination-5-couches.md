# ADR-003 : Stratégie anti-hallucination en 5 couches

**Statut** : Accepté  
**Date** : 2025  
**Décideurs** : Équipe technique  

---

## Contexte

Les modèles LLM (GPT-4o-mini inclus) peuvent produire des affirmations factuellement incorrectes même lorsqu'ils disposent d'un contexte RAG. Dans un domaine où la précision est critique (horaires d'ouverture, adresses, prix, nombre exact de boutiques), une seule hallucination peut nuire à l'expérience client.

L'approche d'une température basse seule (T=0.1) est nécessaire mais insuffisante.

---

## Décision

Implémentation d'un **validateur post-génération en 5 couches** (`_validate_response()` dans `ai_agent.py`), exécuté systématiquement après chaque réponse LLM avant envoi à l'utilisateur.

---

## Les 5 couches de validation

### Couche 1 — Contradiction de boutique
**Détection** : La réponse contient une phrase négative ("n'avons pas de boutique", "malheureusement pas"...) alors que le contexte RAG contient `[boutique trouvé]` ou la mention d'une boutique.  
**Correction** : Appel direct à `get_boutique_info(dept)` pour construire une réponse structurée depuis la KB.

### Couche 2 — Incohérence d'horaires
**Détection** : Les horaires dans la réponse (format HH:MM-HH:MM) ne correspondent pas aux horaires du contexte RAG.  
**Correction** : Remplacement des horaires hallucination par les horaires exacts extraits du contexte.

### Couche 3 — Cohérence département/ville
**Détection** : La requête mentionne un code de département (ex: `75`, `91`), le contexte contient la ville correspondante, mais la réponse dit "pas de boutique".  
**Correction** : Appel à `get_boutique_info(dept)` pour réponse structurée.

### Couche 4 — Comptage de boutiques [CRITIQUE]
**Détection** : Pour les requêtes "combien de boutiques", le nombre mentionné dans la réponse est différent du nombre réel retourné par `get_all_boutiques()`.  
**Correction** : Remplacement par "Nous avons {N} boutiques en France." (N = vérité KB).

### Couche 5 — Hallucination de prix
**Détection** : La réponse mentionne des prix (€) alors que le contexte RAG n'en contient aucun → hallucination pure.  
**Correction secondaire** : Si la réponse mentionne un prix > 2× le maximum du contexte → remplacement par les prix du contexte.

---

## Alternatives écartées

- **Prompt seul** ("Ne mentionne jamais de prix si non présent dans le contexte") : insuffisant, le modèle transgresse parfois les instructions.  
- **Validation par second LLM** : double le coût et la latence.  
- **Score de confiance via logprobs** : non exposé par l'API OpenAI Chat Completions standard.

---

## Conséquences

- **Positives** : Toute réponse incorrecte sur les critères critiques (adresses, horaires, comptages, prix) est interceptée et corrigée avant envoi.
- **Négatives** : Surcoût de traitement minimal (regex + comparaisons string, <1ms). Faux positifs possibles sur la couche horaires si le formatage varie entre contexte et réponse.
- **Évolutivité** : Ajout de nouvelles couches sans impact sur l'architecture (fonctions indépendantes).
