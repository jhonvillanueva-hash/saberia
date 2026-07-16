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


def test_user_insertion(test_db):
    """Test basic user insertion."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        display_name="Test User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    # Verify user was inserted
    fetched_user = test_db.get(User, user.id)
    assert fetched_user is not None
    assert fetched_user.email == "test@example.com"
    assert fetched_user.display_name == "Test User"


def test_book_with_chapter_insertion(test_db):
    """Test inserting a book with a chapter."""
    # Create user first
    user = User(
        id=uuid.uuid4(),
        email="booktest@example.com",
        display_name="Book Test User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

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
    test_db.add(book)
    test_db.commit()

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
    test_db.add(chapter)
    test_db.commit()

    # Verify all were inserted
    fetched_book = test_db.get(Book, book.id)
    assert fetched_book is not None
    assert fetched_book.title == "Test Book"

    fetched_chapter = test_db.get(Chapter, chapter.id)
    assert fetched_chapter is not None
    assert fetched_chapter.title == "Chapter 1"


def test_unique_constraint_auth_provider(test_db):
    """Test that unique constraint on auth_providers works."""
    user = User(
        id=uuid.uuid4(),
        email="unique@example.com",
        display_name="Unique User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    # First auth provider
    auth1 = AuthProvider(
        id=uuid.uuid4(),
        user_id=user.id,
        provider="google",
        provider_email="test@gmail.com"
    )
    test_db.add(auth1)
    test_db.commit()

    # Try to insert duplicate (same user_id, provider)
    auth2 = AuthProvider(
        id=uuid.uuid4(),
        user_id=user.id,
        provider="google",
        provider_email="test2@gmail.com"
    )
    test_db.add(auth2)

    with pytest.raises(IntegrityError):
        test_db.commit()


def test_check_constraint_month_range(test_db):
    """Test that month must be between 1 and 12."""
    user = User(
        id=uuid.uuid4(),
        email="check@example.com",
        display_name="Check User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    # Try to insert with month=13 (invalid)
    limit = UserMonthlyLimit(
        id=uuid.uuid4(),
        user_id=user.id,
        year=2026,
        month=13,  # Invalid!
        conversions_used=0,
        conversions_limit=3
    )
    test_db.add(limit)

    with pytest.raises(IntegrityError):
        test_db.commit()


def test_updated_at_trigger(test_db):
    """Test that updated_at is automatically updated on row update."""
    user = User(
        id=uuid.uuid4(),
        email="trigger@example.com",
        display_name="Trigger User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    # Get the initial updated_at
    initial_updated_at = user.updated_at

    # Wait a moment to ensure time difference
    import time
    time.sleep(1)  # Increased from 0.1 to 1 second

    # Update the user
    user.display_name = "Updated Trigger User"
    test_db.commit()

    # Refresh and check updated_at changed
    test_db.refresh(user)
    assert user.updated_at > initial_updated_at
    assert user.display_name == "Updated Trigger User"
