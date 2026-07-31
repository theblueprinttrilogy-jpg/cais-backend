# Deployment Guide - CAIS Code Compliance

## Overview

CAIS Code Compliance can be deployed in multiple environments:
- Development (local)
- Production (Google Cloud Run)

## Local Development

```bash
# Clone repository
git clone https://github.com/theblueprinttrilogy-jpg/cais-backend.git
cd cais-backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start services with Docker Compose
docker-compose up -d

# Initialize database
python -m app.scripts.init_db

# Seed data
python -m app.scripts.seed_data

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
