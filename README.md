# Terres de Cafe Chatbot AI

Chatbot RAG agentic pour Terres de Cafe (cafes).

## Architecture

- **Backend**: FastAPI + OpenAI GPT-4o-mini
- **RAG**: FAISS semantic search
- **Knowledge Base**: `terres_de_cafe_knowledge.json`

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

Server: http://localhost:8000

## Tests

```bash
python -m pytest tests/ -v
```

## Déploiement

Voir DEPLOYMENT.md pour Render.com

## Configuration Scraper

- **Site**: https://www.terresdecafe.com
- **Méthode**: Crawling automatique (pas de sitemap)
- **Output**: terres_de_cafe_knowledge.json

## Structure

```
ai_agent.py              # 9 tools agentic + validation
rag_engine.py            # FAISS semantic search
knowledge_base_enriched.py  # Domain RAG methods
scraper_industrial_2025.py  # JSON-LD scraper
main.py                  # FastAPI server
```

## Licence

MIT
