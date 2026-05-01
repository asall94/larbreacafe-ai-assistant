# Déploiement L'Arbre � Caf� Chatbot

## Render.com (Recommandé)

1. Push code sur GitHub
2. Créer Web Service sur Render.com
3. Configuration:
   - **Build Command**: `pip install -r requirements.txt && python scraper_industrial_2026.py`
   - **Start Command**: Render détecte automatiquement le Procfile
   - **Environment Variables**: OPENAI_API_KEY
   - **Instance Type**: Free (ou Starter pour production)

## Variables d'environnement

```
OPENAI_API_KEY=sk-...
ENVIRONMENT=production
```

## Health Check

GET /health → 200 OK

## Monitoring

- UptimeRobot pour monitoring 24/7
- Logs via Render dashboard
