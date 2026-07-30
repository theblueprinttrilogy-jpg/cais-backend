#!/bin/bash
# CAIS Code Compliance - Verification Script

echo "🔍 Verifying CAIS Code Compliance deployment..."

# Variables
URL="https://cais-backend-793010740316.us-central1.run.app"

# 1. Health check
echo "📊 Health Check:"
curl -s ${URL}/health | python3 -m json.tool
echo ""

# 2. Root endpoint
echo "📊 Root Endpoint:"
curl -s ${URL}/ | python3 -m json.tool
echo ""

# 3. Ping endpoint
echo "📊 Ping Endpoint:"
curl -s ${URL}/api/v1/ping | python3 -m json.tool
echo ""

# 4. API Docs
echo "📊 API Docs:"
curl -s ${URL}/docs | head -20
echo ""

echo "✅ Verification complete!"
