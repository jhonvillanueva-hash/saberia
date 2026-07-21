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
from app.modules.users.service import get_or_create_monthly_limit, get_current_year_month, MonthlyLimitExceededError
from app.shared.storage import upload_file, delete_file
from app.shared.enums import BookFileType, BookStatus


def create_book(db, user, file_bytes, original_filename, title):
    file_type = detect_file_type(original_filename, file_bytes)
    validate_file_size(file_type, len(file_bytes))

    page_count = None
    word_count = None
    if file_type == BookFileType.pdf:
        page_count = extract_pdf_page_count(file_bytes)
        validate_content_limits(file_type, page_count, None)
    else:
        word_count = extract_epub_word_count(file_bytes)
        validate_content_limits(file_type, None, word_count)

    year, month = get_current_year_month()
    limit_row = get_or_create_monthly_limit(db, user.id, year, month)
    if limit_row.conversions_used >= limit_row.conversions_limit:
        db.rollback()
        raise MonthlyLimitExceededError("Monthly conversion limit reached")

    key = f"books/{user.id}/{uuid4()}_{original_filename}"
    content_type = "application/pdf" if file_type == BookFileType.pdf else "application/epub+zip"
    upload_file(file_bytes, key, content_type)

    try:
        limit_row.conversions_used += 1
        book = Book(
            user_id=user.id,
            title=title,
            original_filename=original_filename,
            original_file_r2_path=key,
            file_type=file_type,
            file_size_bytes=len(file_bytes),
            page_count=page_count,
            word_count=word_count,
            status=BookStatus.pending,
            uploaded_at=datetime.now(timezone.utc)
        )
        db.add(book)
        db.commit()
        db.refresh(book)
        return book
    except Exception:
        db.rollback()
        try:
            delete_file(key)
        except Exception:
            pass
        raise