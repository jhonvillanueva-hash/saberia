from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.shared.enums import BookFileType


class BookResponse(BaseModel):
    id: UUID
    title: str
    author: str | None
    file_type: BookFileType
    status: str
    page_count: int | None
    word_count: int | None
    chapter_count: int
    uploaded_at: datetime
    last_accessed_at: datetime | None

    class Config:
        from_attributes = True