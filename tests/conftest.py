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
    """Create all tables for tests using Alembic migrations."""
    import subprocess
    import sys
    import os

    # Apply migrations using subprocess with correct DATABASE_URL
    env = os.environ.copy()
    env['DATABASE_URL'] = TEST_DATABASE_URL
    result = subprocess.run(
        [sys.executable, '-m', 'alembic', 'upgrade', 'head'],
        check=True,
        env=env,
        cwd=os.getcwd()
    )

    # Create a session
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def test_db(db_session):
    """Provide a clean database session for each test with transaction isolation."""
    # Begin a nested transaction for this test
    connection = db_session.connection()
    transaction = connection.begin_nested()

    # Add a savepoint for rollback
    db_session.begin_nested()

    try:
        yield db_session
    finally:
        # Rollback the nested transaction to clean up test data
        db_session.rollback()
        transaction.rollback()
        connection.close()


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
