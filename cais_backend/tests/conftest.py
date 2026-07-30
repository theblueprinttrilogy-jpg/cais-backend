"""
Conftest - Pytest Configuration and Fixtures

This module provides shared fixtures for all tests.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.core.database import Base, get_db
from app.db.models import User, Project, Document, Violation, CodeReference, Report, Payment, WORMLedgerEntry


# Test database
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def test_db(test_engine) -> Generator[Session, None, None]:
    """Create test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture(scope="function")
def test_client(test_db) -> Generator[TestClient, None, None]:
    """Create test client with database override."""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(test_db) -> User:
    """Create test user."""
    from app.core.jwt import get_password_hash

    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        is_active=True,
        is_verified=True,
        preferred_language="en"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_project(test_db, test_user) -> Project:
    """Create test project."""
    project = Project(
        user_id=test_user.id,
        name="Test Project",
        address="123 Test St, Test City, TC 12345",
        jurisdiction="US-CA",
        description="Test project description",
        status="active"
    )
    test_db.add(project)
    test_db.commit()
    test_db.refresh(project)
    return project


@pytest.fixture(scope="function")
def test_document(test_db, test_project) -> Document:
    """Create test document."""
    document = Document(
        project_id=test_project.id,
        filename="test_document.pdf",
        file_path="/tmp/test_document.pdf",
        file_size=1024,
        file_type="pdf",
        language="en",
        status="pending",
        pages=1
    )
    test_db.add(document)
    test_db.commit()
    test_db.refresh(document)
    return document


@pytest.fixture(scope="function")
def test_code_reference(test_db) -> CodeReference:
    """Create test code reference."""
    code = CodeReference(
        code_type="IBC",
        section="1005.3.1",
        title="Means of Egress Door Width",
        description="Minimum door width for means of egress shall be 32 inches.",
        full_text="1005.3.1 Door Width. The minimum width of each door opening shall be 32 inches (813 mm).",
        jurisdiction="US-CA",
        severity="Critical"
    )
    test_db.add(code)
    test_db.commit()
    test_db.refresh(code)
    return code


@pytest.fixture(scope="function")
def test_violation(test_db, test_document) -> Violation:
    """Create test violation."""
    violation = Violation(
        document_id=test_document.id,
        violation_type="door_width",
        severity="critical",
        description="Door width 30 inches (below standard 32 inches)",
        code_reference="IBC 1005.3.1",
        code_type="IBC",
        section="1005.3.1",
        page_num=1,
        status="detected"
    )
    test_db.add(violation)
    test_db.commit()
    test_db.refresh(violation)
    return violation


@pytest.fixture(scope="function")
def test_worm_entry(test_db) -> WORMLedgerEntry:
    """Create test WORM ledger entry."""
    entry = WORMLedgerEntry(
        evidence_gcs_uri="gs://test/evidence/test.png",
        violation_codes={"code": "IBC 1005.3.1", "description": "Door width violation"},
        cryptographic_hash="test_hash_1234567890"
    )
    test_db.add(entry)
    test_db.commit()
    test_db.refresh(entry)
    return entry
