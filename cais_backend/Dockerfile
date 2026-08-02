# CAIS Code Compliance - Production Dockerfile
# Uses Python 3.11 slim base image for minimal size and security

FROM python:3.11-slim

# Set environment variables for optimal Python and application behavior
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TZ=UTC \
    HF_HOME=/app/model_cache

# Install all required system dependencies in a single layer
# Includes compilers, PostgreSQL client, OCR tools, PDF utilities, and GUI libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    tesseract-ocr \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy requirements file first to leverage Docker caching
COPY requirements.txt .

# Install Python dependencies from the requirements file
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the sentence-transformers model at build time
# This caches the model in /app/model_cache for faster startup
RUN python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy the rest of the application source code
COPY . .

# Expose the default Cloud Run / Uvicorn port
EXPOSE 8080

# Start the FastAPI application using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
