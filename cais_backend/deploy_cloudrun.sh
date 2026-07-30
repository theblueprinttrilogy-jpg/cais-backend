#!/bin/bash
# CAIS Code Compliance - Cloud Run Deployment Script

echo "🚀 Deploying CAIS Code Compliance v10.0 to Cloud Run..."

# Variables
PROJECT_ID="cais-production-system"
SERVICE_NAME="cais-backend"
REGION="us-central1"
IMAGE="us-central1-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}/${SERVICE_NAME}:v10.0"

# Desplegar
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE} \
  --platform managed \
  --region ${REGION} \
  --memory 4Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 10 \
  --allow-unauthenticated \
  --set-env-vars="ENVIRONMENT=production"

# Verificar
echo "✅ Deployment complete!"
echo "📍 URL: https://${SERVICE_NAME}-793010740316.${REGION}.run.app"
