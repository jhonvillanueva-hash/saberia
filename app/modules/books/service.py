from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.modules.users.models import User
from app.modules.books.models import Book
from app.modules.books.validation import (
    detect_file_type,
    validate_file_size,
    extract_pdf_page_count,
    extract_epub_word_count,
    validate_content_limits
)
from app.modules.users.service import consume_conversion_slot, MonthlyLimitExceededError
from app.shared.storage import upload_file, delete_file
from app.shared.enums import BookFileType


def create_book(db: Session, user: User, file_bytes: bytes, original_filename: str, title: str) -> Book:
    file_type = detect_file_type(original_filename, file_bytes)
    validate_file_size(file_type, len(file_bytes))

    if file_type == BookFileType.pdf:
        page_count = extract_pdf_page_count(file_bytes)
        word_count = None
        validate_content_limits(file_type, page_count, None)
    else:
        page_count = None
        word_count = extract_epub_word_count(file_bytes)
        validate_content_limits(file_type, None, word_count)

    consume_conversion_slot(db, user.id)

    key = f"books/{user.id}/{uuid4()}_{original_filename}"
    content_type = "application/pdf" if file_type == BookFileType.pdf else "application/epub+zip"
    upload_file(file_bytes, key, content_type)

    try:
        book = Book(
            user_id=user.id,
            title=title,
            original_filename=original_filename,
            original_file_r2_path=key,
            file_type=file_type,
            file_size_bytes=len(file_bytes),
            page_count=page_count,
            word_count=word_count,
            status="pending",
            uploaded_at=datetime.now(timezone.utc)
        )
        db.add(book)
        db.commit()
        return book
    except Exception:
        db.rollback()
        try:
            delete_file(key)
        except Exception:
            pass
        raise