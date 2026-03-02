# L'Arbre à Café Chatbot AI

Chatbot RAG agentic pour L'Arbre à Café, torréfacteur de cafés de spécialité depuis 2009.

## Architecture

- **Backend**: FastAPI (Python 3.12) + 6 outils agentiques
- **RAG**: FAISS IndexFlatIP (5-10ms)
- **LLM**: OpenAI GPT-4o-mini (temp=0.1) + text-embedding-ada-002
- **Validation**: 5 couches anti-hallucination
- **Knowledge Base**: `larbrecaf_knowledge_industrial_2025.json` (v4.0_industrial)
- **Déploiement**: Render.com (auto-deploy sur push `main`)

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
python -m pytest -v
```

## Déploiement

Voir DEPLOYMENT.md pour Render.com

## Configuration Scraper

- **Site**: https://larbreacafe.com
- **Méthode**: Crawling automatique (pas de sitemap)
- **Output**: `larbrecaf_knowledge_industrial_2025.json`
- **Dernière exécution**: 2026-03-02 (98 pages, 5 boutiques)

## Outils agentiques (6)

| Outil | Rôle |
|---|---|
| `search_knowledge` | Recherche sémantique FAISS |
| `get_boutiques` | Liste toutes les boutiques |
| `get_boutique_info` | Infos boutique par ville |
| `get_contact` | Téléphone/adresse par ville |
| `get_hours` | Horaires d'ouverture |
| `find_nearest_boutique` | Boutique la plus proche |

## Structure

```
ai_agent.py                          # 6 outils agentiques + validation 5 couches
rag_engine.py                        # FAISS IndexFlatIP
knowledge_base_enriched.py           # Méthodes RAG domaine
scraper_industrial_2025.py           # Scraper JSON-LD + HTML
larbrecaf_knowledge_industrial_2025.json  # Source de vérité unique
main.py                              # Serveur FastAPI
logger_config.py                     # Logging JSON structuré
validate_responses.py                # Validation réponses standalone
run_simulation.py                    # Simulation de conversations
```

## Licence

MIT
