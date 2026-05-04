#!/usr/bin/env bash
set -e  # Exit immediately if any command fails

echo "==> Running database migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Seeding symptoms, diseases and urgency rules..."
python manage.py load_csv_data

echo "==> Indexing knowledge base into ChromaDB..."
python manage.py index_knowledge_base

echo "==> Build complete. Starting server..."
