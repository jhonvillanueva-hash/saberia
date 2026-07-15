import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.modules.users.models import User, UserMonthlyLimit
from app.modules.auth.models import AuthProvider
from app.modules.books.models import Book, ProcessingJob, Chapter, ChapterAudio
from app.modules.listening.models import ListeningProgress


def test_tables_exist(db_session):
    """Test that all tables are created."""
    # This test passes if Base.metadata.create_all() in conftest.py succeeds
    assert True


def test_user_insertion(db_session):
    """Test basic user insertion."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        display_name="Test User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()

    # Verify user was inserted
    fetched_user = db_session.get(User, user.id)
    assert fetched_user is not None
    assert fetched_user.email == "test@example.com"
    assert fetched_user.display_name == "Test User"


def test_book_with_chapter_insertion(db_session):
    """Test inserting a book with a chapter."""
    # Create user first
    user = User(
        id=uuid.uuid4(),
        email="booktest@example.com",
        display_name="Book Test User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()

    # Create book
    book = Book(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Test Book",
        author="Test Author",
        original_filename="test.pdf",
        original_file_r2_path="/books/test.pdf",
        file_type="pdf",
        file_size_bytes=1024,
        chapter_count=1
    )
    db_session.add(book)
    db_session.commit()

    # Create chapter
    chapter = Chapter(
        id=uuid.uuid4(),
        book_id=book.id,
        chapter_number=1,
        title="Chapter 1",
        order_index=1,
        extracted_text="This is the extracted text.",
        word_count=5
    )
    db_session.add(chapter)
    db_session.commit()

    # Verify all were inserted
    fetched_book = db_session.get(Book, book.id)
    assert fetched_book is not None
    assert fetched_book.title == "Test Book"

    fetched_chapter = db_session.get(Chapter, chapter.id)
    assert fetched_chapter is not None
    assert fetched_chapter.title == "Chapter 1"


def test_unique_constraint_auth_provider(db_session):
    """Test that unique constraint on auth_providers works."""
    user = User(
        id=uuid.uuid4(),
        email="unique@example.com",
        display_name="Unique User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()

    # First auth provider
    auth1 = AuthProvider(
        id=uuid.uuid4(),
        user_id=user.id,
        provider="google",
        provider_email="test@gmail.com"
    )
    db_session.add(auth1)
    db_session.commit()

    # Try to insert duplicate (same user_id, provider)
    auth2 = AuthProvider(
        id=uuid.uuid4(),
        user_id=user.id,
        provider="google",
        provider_email="test2@gmail.com"
    )
    db_session.add(auth2)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_check_constraint_month_range(db_session):
    """Test that month must be between 1 and 12."""
    user = User(
        id=uuid.uuid4(),
        email="check@example.com",
        display_name="Check User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()

    # Try to insert with month=13 (invalid)
    limit = UserMonthlyLimit(
        id=uuid.uuid4(),
        user_id=user.id,
        year=2026,
        month=13,  # Invalid!
        conversions_used=0,
        conversions_limit=3
    )
    db_session.add(limit)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_updated_at_trigger(db_session):
    """Test that updated_at is automatically updated on row update."""
    user = User(
        id=uuid.uuid4(),
        email="trigger@example.com",
        display_name="Trigger User",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()

    # Get the initial updated_at
    initial_updated_at = user.updated_at

    # Wait a moment to ensure time difference
    import time
    time.sleep(0.1)

    # Update the user
    user.display_name = "Updated Trigger User"
    db_session.commit()

    # Refresh and check updated_at changed
    db_session.refresh(user)
    assert user.updated_at > initial_updated_at
    assert user.display_name == "Updated Trigger User"
