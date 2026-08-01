#!/bin/bash
# Despliegue de la próxima revisión con psycopg2

gcloud run deploy cais-backend \
    --project=cais-production-system \
    --region=us-central1 \
    --image=us-central1-docker.pkg.dev/cais-production-system/cais-backend/cais-backend:test \
    --update-secrets=DATABASE_URL=DATABASE_URL:latest \
    --memory=2Gi \
    --cpu=1 \
    --max-instances=10 \
    --min-instances=0 \
    --port=8000 \
    --timeout=3600 \
    --allow-unauthenticated \
    --no-traffic
