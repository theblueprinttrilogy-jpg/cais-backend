# API Reference - CAIS Code Compliance

## Base URL

https://cais-backend-793010740316.us-central1.run.app

## Authentication

### Register User

**Endpoint:** POST /api/v1/auth/register

**Request Body:**
{
  "email": "user@example.com",
  "username": "username",
  "password": "SecurePass123!",
  "full_name": "Full Name",
  "language": "en"
}

**Response:** 201 Created
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "username",
  "full_name": "Full Name",
  "is_active": true,
  "subscription_plan": "free",
  "created_at": "2026-07-30T00:00:00"
}

### Login

**Endpoint:** POST /api/v1/auth/login

**Request Body (form-data):**
username: user@example.com
password: SecurePass123!

**Response:** 200 OK
{
  "access_token": "jwt_token",
  "refresh_token": "jwt_refresh_token",
  "token_type": "bearer",
  "expires_in": 1800
}

### Refresh Token

**Endpoint:** POST /api/v1/auth/refresh

**Request Body:**
{
  "refresh_token": "jwt_refresh_token"
}

**Response:** 200 OK
{
  "access_token": "jwt_token",
  "refresh_token": "jwt_refresh_token",
  "token_type": "bearer",
  "expires_in": 1800
}

### Logout

**Endpoint:** POST /api/v1/auth/logout

**Headers:** Authorization: Bearer {access_token}

**Response:** 200 OK
{
  "message": "Successfully logged out"
}

---

## Users

### Get Current User

**Endpoint:** GET /api/v1/users/me

**Headers:** Authorization: Bearer {access_token}

**Response:** 200 OK
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "username",
  "full_name": "Full Name",
  "is_active": true,
  "is_superuser": false,
  "subscription_plan": "free",
  "trial_end_date": "2026-08-30T00:00:00",
  "created_at": "2026-07-30T00:00:00"
}

### Update Current User

**Endpoint:** PUT /api/v1/users/me

**Headers:** Authorization: Bearer {access_token}

**Request Body:**
{
  "full_name": "Updated Name",
  "preferred_language": "es"
}

**Response:** 200 OK

---

## Projects

### List Projects

**Endpoint:** GET /api/v1/projects

**Headers:** Authorization: Bearer {access_token}

**Response:** 200 OK
[
  {
    "id": "uuid",
    "name": "Project Name",
    "address": "123 Main St",
    "jurisdiction": "US-CA",
    "status": "active",
    "created_at": "2026-07-30T00:00:00"
  }
]

### Create Project

**Endpoint:** POST /api/v1/projects

**Headers:** Authorization: Bearer {access_token}

**Request Body:**
{
  "name": "New Project",
  "address": "123 Main St, Los Angeles, CA",
  "jurisdiction": "US-CA",
  "description": "Project description"
}

**Response:** 201 Created

---

## Upload

### Upload Document

**Endpoint:** POST /api/v1/upload/file

**Headers:** Authorization: Bearer {access_token}

**Request:** multipart/form-data
file: <PDF file>

**Response:** 200 OK
{
  "status": "success",
  "message": "File uploaded successfully",
  "data": {
    "job_id": "uuid",
    "filename": "document.pdf",
    "status": "processing"
  }
}

### Get Processing Status

**Endpoint:** GET /api/v1/upload/status/{job_id}

**Headers:** Authorization: Bearer {access_token}

**Response:** 200 OK
{
  "status": "success",
  "data": {
    "job_id": "uuid",
    "filename": "document.pdf",
    "overall_status": "completed",
    "steps": {
      "ocr": {"status": "done", "timestamp": "2026-07-30T00:00:00"},
      "analysis": {"status": "done", "timestamp": "2026-07-30T00:00:00"}
    },
    "results": {
      "address": "123 Main St",
      "jurisdiction": "US-CA",
      "analysis": {
        "total_violations": 3,
        "severity_breakdown": {"critical": 1, "high": 2}
      }
    }
  }
}

---

## Analysis

### Start Analysis

**Endpoint:** POST /api/v1/analysis/{task_id}/start

**Headers:** Authorization: Bearer {access_token}

**Response:** 200 OK
{
  "status": "started",
  "task_id": "uuid",
  "message": "Analysis started"
}

### Get Analysis Status

**Endpoint:** GET /api/v1/analysis/{task_id}/status

**Headers:** Authorization: Bearer {access_token}

**Response:** 200 OK
{
  "task_id": "uuid",
  "status": "completed",
  "progress": 100,
  "violations_found": 3,
  "pages_processed": 5,
  "created_at": "2026-07-30T00:00:00",
  "updated_at": "2026-07-30T00:00:00"
}

### Get Analysis Results

**Endpoint:** GET /api/v1/analysis/{task_id}/results

**Headers:** Authorization: Bearer {access_token}

**Response:** 200 OK
{
  "task_id": "uuid",
  "document_id": "uuid",
  "status": "completed",
  "total_violations": 3,
  "violations": [
    {
      "id": "uuid",
      "type": "door_width",
      "severity": "critical",
      "description": "Door width 30 inches (below standard 32 inches)",
      "code_reference": "IBC 1005.3.1",
      "page_num": 1,
      "evidence_path": "/storage/evidence/evidence_xxx.png",
      "status": "detected"
    }
  ],
  "language": "en",
  "pages": 5,
  "completed_at": "2026-07-30T00:00:00"
}

---

## Reports

### Download Report

**Endpoint:** GET /api/v1/reports/{task_id}/download

**Headers:** Authorization: Bearer {access_token}

**Response:** application/pdf file

### Get Report Status

**Endpoint:** GET /api/v1/reports/{task_id}/status

**Headers:** Authorization: Bearer {access_token}

**Response:** 200 OK
{
  "task_id": "uuid",
  "status": "completed",
  "download_count": 3,
  "language": "en",
  "generated_at": "2026-07-30T00:00:00"
}

---

## Subscriptions

### Get Available Plans

**Endpoint:** GET /api/v1/subscriptions/plans

**Response:** 200 OK
{
  "free": {
    "name": "Free Trial",
    "days": 30,
    "price": 0,
    "currency": "USD",
    "features": ["Basic Analysis", "1 Project", "Forensic Facts Dossier"]
  },
  "monthly": {
    "name": "Monthly Plan",
    "days": 30,
    "price": 299.00,
    "currency": "USD",
    "features": ["Unlimited Projects", "All Agents", "Full Reports", "Priority Support"]
  },
  "annual": {
    "name": "Annual Plan",
    "days": 365,
    "price": 2999.00,
    "currency": "USD",
    "features": ["Unlimited Projects", "All Agents", "Full Reports", "Priority Support", "2 Months Free", "Dedicated Account Manager"]
  }
}

### Get Current Subscription

**Endpoint:** GET /api/v1/subscriptions/current

**Headers:** Authorization: Bearer {access_token}

**Response:** 200 OK
{
  "user_id": "uuid",
  "plan": "free",
  "status": "active",
  "trial_end_date": "2026-08-30T00:00:00",
  "features": ["Basic Analysis", "1 Project", "Forensic Facts Dossier"],
  "days_left": 30,
  "is_trial": true
}

### Upgrade Subscription

**Endpoint:** POST /api/v1/subscriptions/upgrade/{plan}

**Headers:** Authorization: Bearer {access_token}

**Response:** 200 OK
{
  "success": true,
  "plan": "monthly",
  "message": "Successfully upgraded to monthly plan"
}

---

## Kill Switch

### Activate Kill Switch

**Endpoint:** POST /api/v1/kill/{task_id}

**Headers:** Authorization: Bearer {access_token}

**Response:** 200 OK
{
  "status": "killed",
  "task_id": "uuid",
  "containers_destroyed": 0,
  "files_cleaned": 0,
  "timestamp": "2026-07-30T00:00:00"
}

## Error Responses

### 400 Bad Request
{
  "error": "Validation error",
  "code": "VALIDATION_ERROR",
  "timestamp": "2026-07-30T00:00:00"
}

### 401 Unauthorized
{
  "error": "Unauthorized",
  "code": "UNAUTHORIZED",
  "timestamp": "2026-07-30T00:00:00"
}

### 403 Forbidden
{
  "error": "Forbidden",
  "code": "FORBIDDEN",
  "timestamp": "2026-07-30T00:00:00"
}

### 404 Not Found
{
  "error": "Resource not found",
  "code": "NOT_FOUND",
  "timestamp": "2026-07-30T00:00:00"
}

### 429 Rate Limit Exceeded
{
  "error": "Rate limit exceeded. Please try again later.",
  "timestamp": "2026-07-30T00:00:00"
}

### 500 Internal Server Error
{
  "error": "Internal server error",
  "timestamp": "2026-07-30T00:00:00"
}

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| Authentication | 20 requests | 60 seconds |
| Upload | 10 requests | 300 seconds |
| Analysis | 30 requests | 60 seconds |
| Default | 100 requests | 60 seconds |
