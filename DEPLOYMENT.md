# Railway Deployment Checklist for Health Chatbot

## Pre-Deployment Steps

### 1. Generate a New Secure SECRET_KEY
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
Copy the output and save it — you'll add it to Railway in step 3.

### 2. Ensure All Files Are Committed
```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

### 3. Create Railway Project & Set Environment Variables

On Railway.app:
1. Create a new project
2. Connect your GitHub repository
3. Add environment variables in Railway settings:

```
DJANGO_SECRET_KEY = <your-newly-generated-secret-key-from-step-1>
DEBUG = False
GROQ_API_KEY = <your-groq-api-key>
ALLOWED_HOSTS = <railway-auto-domain>
CORS_ALLOWED_ORIGINS = https://<railway-auto-domain>
```

### 4. Deployment

- Push to your main branch, Railway will auto-deploy
- Check Railway logs for any errors
- Visit your app URL to test

## Environment Variables Explained

| Variable | Purpose | Local | Railway |
|----------|---------|-------|---------|
| `DJANGO_SECRET_KEY` | Django security key | .env | Railway variables |
| `SECRET_KEY` | Alternative name for Django key | .env | — |
| `DEBUG` | Development/Production mode | True | False |
| `GROQ_API_KEY` | LLM API key | .env | Railway variables |
| `ALLOWED_HOSTS` | Allowed domain names | localhost,127.0.0.1 | railway-domain |
| `CORS_ALLOWED_ORIGINS` | Allowed frontend origins | http://localhost:5173 | https://your-frontend |

## Files for Deployment

- `Procfile` — How to run the app on Railway
- `runtime.txt` — Python version specification
- `requirements.txt` — All Python dependencies
- `.env` — Local development (NOT committed, Railway uses Variables)

## Testing Before Deploy

```bash
# Build and run locally with production settings
DEBUG=False DJANGO_SECRET_KEY=test-key python manage.py runserver
```

## Post-Deployment

1. Run migrations: `python manage.py migrate`
2. Create superuser (optional): `python manage.py createsuperuser`
3. Test endpoints via Postman or curl
4. Check logs in Railway dashboard for errors

## Troubleshooting

- **SECRET_KEY error**: Ensure DJANGO_SECRET_KEY is set in Railway variables
- **Database error**: SQLite works for small apps; consider PostgreSQL for production
- **CORS errors**: Add frontend URL to CORS_ALLOWED_ORIGINS
- **Static files 404**: WhiteNoise middleware handles this automatically

## Optional: Use PostgreSQL Instead of SQLite

1. Add Railway PostgreSQL plugin
2. Copy DATABASE_URL from Railway
3. Install `psycopg2-binary` in requirements.txt
4. Update settings.py to use DATABASE_URL:

```python
import dj-database-url
DATABASES = {
    'default': dj_database_url.config(conn_max_age=600)
}
```
