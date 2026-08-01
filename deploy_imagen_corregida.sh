#!/bin/bash
# Despliegue de la imagen corregida con fake-useragent

echo "🚀 Desplegando imagen corregida..."
gcloud run deploy cais-backend \
    --project=cais-production-system \
    --region=us-central1 \
    --image=us-central1-docker.pkg.dev/cais-production-system/cais-backend/cais-backend:fixed \
    --update-secrets=DATABASE_URL=DATABASE_URL:latest \
    --memory=2Gi \
    --cpu=1 \
    --max-instances=10 \
    --min-instances=0 \
    --port=8000 \
    --timeout=3600 \
    --allow-unauthenticated \
    --no-traffic

echo "✅ Despliegue completado. Verifica con:"
echo "gcloud run revisions list --project=cais-production-system --region=us-central1 --service=cais-backend"
