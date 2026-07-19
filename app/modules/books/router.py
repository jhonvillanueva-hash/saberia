from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.users.models import User
from app.modules.books.models import Book
from app.modules.books.schemas import BookResponse
from app.modules.books.service import create_book, MonthlyLimitExceededError
from app.modules.auth.dependencies import get_current_user


router = APIRouter(prefix="/books", tags=["books"])


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def upload_book(
    file: UploadFile,
    title: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_bytes = await file.read()
    original_filename = file.filename

    if not title:
        title = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename

    try:
        book = create_book(db, current_user, file_bytes, original_filename, title)
        return book
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except MonthlyLimitExceededError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly conversion limit reached"
        )


@router.get("", response_model=list[BookResponse])
def list_books(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    books = db.query(Book).\
        filter(Book.user_id == current_user.id, Book.deleted_at.is_(None)).\
        order_by(Book.created_at.desc()).\
        all()
    return books


@router.get("/{book_id}", response_model=BookResponse)
def get_book(
    book_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    book = db.query(Book).\
        filter(Book.id == book_id, Book.user_id == current_user.id, Book.deleted_at.is_(None)).\
        first()

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    return book


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    book_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    book = db.query(Book).\
        filter(Book.id == book_id, Book.user_id == current_user.id, Book.deleted_at.is_(None)).\
        first()

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )

    book.deleted_at = datetime.now(timezone.utc)
    db.commit()