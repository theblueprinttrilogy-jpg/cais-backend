"""
Test Auth - Tests for Authentication Endpoints

This module contains tests for authentication endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestAuth:
    """Tests for authentication endpoints."""

    def test_register_user(self, test_client: TestClient):
        """Test user registration."""
        response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "SecurePass123!",
                "full_name": "New User",
                "language": "en"
            }
        )
        assert response.status_code == 201

        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert data["full_name"] == "New User"
        assert data["is_active"] is True
        assert "id" in data

    def test_register_duplicate_email(self, test_client: TestClient, test_user):
        """Test registration with duplicate email."""
        response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "anotheruser",
                "password": "SecurePass123!",
                "full_name": "Another User"
            }
        )
        assert response.status_code == 409
        assert "Email already registered" in response.text

    def test_register_duplicate_username(self, test_client: TestClient, test_user):
        """Test registration with duplicate username."""
        response = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "another@example.com",
                "username": "testuser",
                "password": "SecurePass123!",
                "full_name": "Another User"
            }
        )
        assert response.status_code == 409
        assert "Username already taken" in response.text

    def test_login_success(self, test_client: TestClient, test_user):
        """Test successful login."""
        response = test_client.post(
            "/api/v1/auth/login",
            data={
                "username": "test@example.com",
                "password": "testpassword123"
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 1800

    def test_login_invalid_credentials(self, test_client: TestClient):
        """Test login with invalid credentials."""
        response = test_client.post(
            "/api/v1/auth/login",
            data={
                "username": "wrong@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.text

    def test_login_invalid_password(self, test_client: TestClient, test_user):
        """Test login with invalid password."""
        response = test_client.post(
            "/api/v1/auth/login",
            data={
                "username": "test@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.text
