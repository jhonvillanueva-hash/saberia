import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from sqlalchemy import event

from fastapi import status, UploadFile
from sqlalchemy.orm import Session

from app.modules.users.models import User
from app.modules.books.models import Book
from app.modules.books.service import create_book, MonthlyLimitExceededError
from app.modules.auth.security import create_access_token


@pytest.fixture
def mock_storage(monkeypatch):
    mock_upload = MagicMock(return_value="books/user-id/file.pdf")
    mock_delete = MagicMock()

    with patch('app.modules.books.service.upload_file', mock_upload), \
         patch('app.modules.books.service.delete_file', mock_delete):
        yield mock_upload, mock_delete


def generate_valid_pdf():
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)

    from io import BytesIO
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def generate_valid_epub():
    from io import BytesIO
    from zipfile import ZipFile

    buffer = BytesIO()
    with ZipFile(buffer, 'w') as zipf:
        zipf.writestr('mimetype', 'application/epub+zip')
        zipf.writestr('content.xhtml', '<html><body><p>Test content for word count</p></body></html>')

    return buffer.getvalue()


def test_upload_valid_pdf(client: Session, test_db: Session, mock_storage):
    mock_upload, mock_delete = mock_storage

    user = User(
        id=uuid.uuid4(),
        email="pdf@example.com",
        display_name="PDF User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    access_token = create_access_token(user.id)

    pdf_bytes = generate_valid_pdf()

    response = client.post(
        "/books",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == status.HTTP_201_CREATED
    mock_upload.assert_called_once()

    book_data = response.json()
    assert book_data["title"] == "test"
    assert book_data["file_type"] == "pdf"
    assert book_data["status"] == "pending"
    assert book_data["page_count"] == 2


def test_upload_valid_epub(client: Session, test_db: Session, mock_storage):
    mock_upload, mock_delete = mock_storage

    user = User(
        id=uuid.uuid4(),
        email="epub@example.com",
        display_name="EPUB User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    access_token = create_access_token(user.id)

    epub_bytes = generate_valid_epub()

    response = client.post(
        "/books",
        files={"file": ("test.epub", epub_bytes, "application/epub+zip")},
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == status.HTTP_201_CREATED
    mock_upload.assert_called_once()

    book_data = response.json()
    assert book_data["title"] == "test"
    assert book_data["file_type"] == "epub"
    assert book_data["status"] == "pending"
    assert book_data["word_count"] > 0


def test_upload_invalid_pdf_extension(client: Session, test_db: Session, mock_storage):
    mock_upload, mock_delete = mock_storage

    user = User(
        id=uuid.uuid4(),
        email="invalid@example.com",
        display_name="Invalid User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    access_token = create_access_token(user.id)

    invalid_bytes = b"Not a PDF file"

    response = client.post(
        "/books",
        files={"file": ("test.pdf", invalid_bytes, "application/pdf")},
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert not mock_upload.called


def test_upload_exceeds_size_limit(client: Session, test_db: Session, mock_storage):
    mock_upload, mock_delete = mock_storage

    user = User(
        id=uuid.uuid4(),
        email="large@example.com",
        display_name="Large User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    access_token = create_access_token(user.id)

    large_bytes = b"X" * (51 * 1024 * 1024)

    response = client.post(
        "/books",
        files={"file": ("large.pdf", large_bytes, "application/pdf")},
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert not mock_upload.called


def test_upload_exceeds_monthly_limit(client: Session, test_db: Session, mock_storage):
    mock_upload, mock_delete = mock_storage

    user = User(
        id=uuid.uuid4(),
        email="limit@example.com",
        display_name="Limit User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    access_token = create_access_token(user.id)

    pdf_bytes = generate_valid_pdf()

    for i in range(3):
        response = client.post(
            "/books",
            files={"file": (f"test{i}.pdf", pdf_bytes, "application/pdf")},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == status.HTTP_201_CREATED

    mock_upload.reset_mock()
    response = client.post(
        "/books",
        files={"file": ("test4.pdf", pdf_bytes, "application/pdf")},
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    mock_upload.assert_not_called()


def test_list_books(client: Session, test_db: Session, mock_storage):
    mock_upload, mock_delete = mock_storage

    user = User(
        id=uuid.uuid4(),
        email="list@example.com",
        display_name="List User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    access_token = create_access_token(user.id)

    pdf_bytes = generate_valid_pdf()

    for i in range(3):
        client.post(
            "/books",
            files={"file": (f"book{i}.pdf", pdf_bytes, "application/pdf")},
            headers={"Authorization": f"Bearer {access_token}"}
        )

    response = client.get(
        "/books",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 3


def test_get_book_not_found(client: Session, test_db: Session):
    user = User(
        id=uuid.uuid4(),
        email="notfound@example.com",
        display_name="Not Found User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    access_token = create_access_token(user.id)

    response = client.get(
        "/books/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_book(client: Session, test_db: Session, mock_storage):
    mock_upload, mock_delete = mock_storage

    user = User(
        id=uuid.uuid4(),
        email="delete@example.com",
        display_name="Delete User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    access_token = create_access_token(user.id)

    pdf_bytes = generate_valid_pdf()

    upload_response = client.post(
        "/books",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
        headers={"Authorization": f"Bearer {access_token}"}
    )

    book_id = upload_response.json()["id"]

    delete_response = client.delete(
        f"/books/{book_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    list_response = client.get(
        "/books",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert len(list_response.json()) == 0

    deleted_book = test_db.query(Book).filter(Book.id == book_id).first()
    assert deleted_book is not None
    assert deleted_book.deleted_at is not None


def test_delete_nonexistent_book(client: Session, test_db: Session):
    user = User(
        id=uuid.uuid4(),
        email="delete2@example.com",
        display_name="Delete 2 User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    access_token = create_access_token(user.id)

    response = client.delete(
        "/books/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_r2_cleanup_on_db_failure(client, test_db, mock_storage):
    mock_upload, mock_delete = mock_storage

    user = User(
        id=uuid.uuid4(),
        email="cleanup@example.com",
        display_name="Cleanup User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()

    access_token = create_access_token(user.id)
    pdf_bytes = generate_valid_pdf()

    def fail_on_book_flush(session, flush_context, instances):
        for obj in session.new:
            if isinstance(obj, Book):
                raise Exception("simulated db failure")

    event.listen(test_db, "before_flush", fail_on_book_flush)
    try:
        with pytest.raises(Exception, match="simulated db failure"):
            client.post(
                "/books",
                files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
                headers={"Authorization": f"Bearer {access_token}"}
            )
    finally:
        event.remove(test_db, "before_flush", fail_on_book_flush)

    mock_upload.assert_called_once()
    uploaded_key = mock_upload.call_args[0][1]
    mock_delete.assert_called_once_with(uploaded_key)


