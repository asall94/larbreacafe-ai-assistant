# L'Arbre à Café — Chatbot Agentic RAG

Assistant IA pour L'Arbre à Café, torréfacteur parisien de cafés de spécialité depuis 2009.  
Architecture **100% agentic RAG** : chaque réponse est construite par sélection dynamique d'outils,
recherche sémantique dans la base de connaissance, et validation anti-hallucination en 5 couches.

## Pourquoi une architecture agentique ?

Un RAG classique (retrieval + génération) ne suffit pas : les requêtes clients mélangent plusieurs
intentions (localisation, horaires, contact, produits). L'orchestration agentique décompose chaque
requête en étapes explicites, sélectionne les outils pertinents, et contrôle finement le contexte
transmis au LLM — garantissant des réponses précises sans donnée inventée.

```
Query → Planning LLM (T=0.3) → Sélection outils (max 3) → Exécution RAG/KB
      → Contexte récupéré → Génération LLM (T=0.1) → Validation 5 couches → Réponse
```

## Stack

- **Backend**: FastAPI (Python 3.12) + orchestration agentique sur mesure
- **Outils**: 7 outils spécialisés (voir tableau ci-dessous)
- **RAG**: FAISS IndexFlatL2 (<10ms latence) + embeddings OpenAI text-embedding-ada-002
- **LLM**: GPT-4o-mini (temp=0.1 génération / temp=0.3 planning)
- **Validation**: 5 couches anti-hallucination post-génération
- **Knowledge Base**: `larbrecaf_knowledge_industrial_2025.json` (v4.0_industrial — source de vérité unique)
- **Tests**: 71/71 tests unitaires (pytest)
- **ADR**: 6 Architecture Decision Records (`docs/adr/`)
- **Déploiement**: Render.com + UptimeRobot (99.5% uptime, auto-deploy sur push `main`)

## Quick Start

```bash
# 1. Environnement
pip install -r requirements.txt

# 2. Configuration
cp .env.example .env
# Ajouter OPENAI_API_KEY dans .env

# 3. Scraping + Build KB
python scraper_industrial_2025.py

# 4. Lancer serveur
python main.py
```

Server: http://localhost:8002

## Tests

```bash
python -m pytest tests/ -v
```

71 tests unitaires couvrant :
- `tests/test_knowledge_base.py` — Haversine, recherche boutique, horaires, contacts
- `tests/test_agent_validation.py` — Les 5 couches anti-hallucination
- `tests/test_agent_tools.py` — Routing d'outils, formatage, mémoire conversation
- `tests/test_rag_engine.py` — Préparation documents, chargement KB

## Déploiement

Voir DEPLOYMENT.md pour Render.com

## Configuration Scraper

- **Site**: https://larbreacafe.com
- **Méthode**: Crawling automatique (pas de sitemap)
- **Output**: `larbrecaf_knowledge_industrial_2025.json`
- **Dernière exécution**: 2026-03-16 (836 pages, 5 boutiques)

## Outils agentiques (7)

Les 7 outils correspondent aux intentions client identifiées. Le LLM de planning sélectionne
jusqu'à 3 outils par requête et paramètre chaque appel dynamiquement (ville, query...).

| Outil | Intention couverte |
|---|---|
| `search_knowledge` | Recherche sémantique FAISS — cafés, origines, torréfaction, livraison, prix |
| `get_boutiques` | Liste complète des boutiques avec adresses et liens |
| `get_boutique_info` | Infos détaillées d'une boutique par ville, rue ou arrondissement |
| `get_contact` | Téléphone et adresse d'une boutique spécifique |
| `get_hours` | Horaires d'ouverture (toutes boutiques ou spécifique) |
| `find_nearest_boutique` | Boutique la plus proche via Haversine + géocodage Nominatim |
| `get_general_info` | Concept, réduction 1ère commande, services, réseaux sociaux |

## Structure

```
ai_agent.py                          # 7 outils agentiques + validation 5 couches
rag_engine.py                        # FAISS IndexFlatL2 (<10ms)
knowledge_base_enriched.py           # Méthodes RAG domaine
scraper_industrial_2025.py           # Scraper JSON-LD + HTML
larbrecaf_knowledge_industrial_2025.json  # Source de vérité unique
main.py                              # Serveur FastAPI
logger_config.py                     # Logging JSON structuré
run_simulation.py                    # Simulation de conversations
tests/                               # 71 tests unitaires (pytest)
docs/adr/                            # 6 Architecture Decision Records
```

## Licence

MIT
