# Dockerfile for CAIS Code Compliance Backend
# Uses Python 3.11 slim image for a lightweight production environment

FROM python:3.11-slim

# Set environment variables to avoid interactive prompts and ensure Python output is logged
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required for building Python packages and PostgreSQL connectivity
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies without caching to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download and cache the sentence-transformers model to avoid runtime downloads
# This ensures the model is available offline during application startup
RUN python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy the rest of the application source code into the container
COPY . .

# Expose the port the application will run on
EXPOSE 8080

# Set the default command to run the FastAPI application with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
