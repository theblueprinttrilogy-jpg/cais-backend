"""
Test Main - Tests for Main Application Endpoints

This module contains tests for the main application endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestMain:
    """Tests for main application endpoints."""

    def test_health_check(self, test_client: TestClient):
        """Test health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "10.0"
        assert data["service"] == "CAIS Code Compliance"
        assert "timestamp" in data

    def test_root_endpoint(self, test_client: TestClient):
        """Test root endpoint."""
        response = test_client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "CAIS Code Compliance"
        assert data["version"] == "10.0"
        assert data["status"] == "operational"
        assert data["documentation"] == "/docs"
        assert data["health"] == "/health"

    def test_docs_endpoint(self, test_client: TestClient):
        """Test docs endpoint."""
        response = test_client.get("/docs")
        assert response.status_code == 200

    def test_redoc_endpoint(self, test_client: TestClient):
        """Test redoc endpoint."""
        response = test_client.get("/redoc")
        assert response.status_code == 200

    def test_openapi_endpoint(self, test_client: TestClient):
        """Test openapi endpoint."""
        response = test_client.get("/openapi.json")
        assert response.status_code == 200

        data = response.json()
        assert data["info"]["title"] == "CAIS Code Compliance API"
        assert data["info"]["version"] == "10.0"

    def test_ping_endpoint(self, test_client: TestClient):
        """Test API v1 ping endpoint."""
        response = test_client.get("/api/v1/ping")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "pong"
        assert data["version"] == "v1"
