import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from app.core.database import Base, get_db
from app.main import app
from app.core.config import settings
from fastapi.testclient import TestClient

# Load environment variables
load_dotenv()

# Use TEST_DATABASE_URL for testing
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/saberia_test")

# Create test engine
test_engine = create_engine(TEST_DATABASE_URL)

# Create session factory for tests
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session")
def db_session():
    """Create and drop all tables for tests."""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    # Create a session
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after tests
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def test_db(db_session):
    """Provide a clean database session for each test."""
    # Create a new session for this test
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client that uses the test database."""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    # Override the dependency
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    # Clean up
    app.dependency_overrides.clear()
