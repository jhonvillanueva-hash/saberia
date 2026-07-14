import os
from sqlalchemy import text
from dotenv import load_dotenv

from app.core.database import get_db, Base

# Load environment variables
load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/saberia_test")


def test_get_db_is_generator():
    """Test that get_db() behaves as a generator and returns a usable session."""
    # Use get_db() directly as a generator (not through FastAPI dependency injection)
    db_gen = get_db()

    # This would fail with @contextmanager because it returns a context manager,
    # not a generator that FastAPI can iterate over
    db = next(db_gen)

    # Verify it's a usable database session
    result = db.execute(text("SELECT 1"))
    assert result.scalar() == 1

    # Verify the generator can be closed properly
    try:
        next(db_gen)  # This should raise StopIteration
        assert False, "Generator should have ended"
    except StopIteration:
        pass  # Expected behavior

    # Verify the session is closed (or can be closed)
    db.close()