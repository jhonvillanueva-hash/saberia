from sqlalchemy import Column, DateTime, Integer, func, UniqueConstraint, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import expression
import uuid

from app.core.database import Base


class ListeningProgress(Base):
    __tablename__ = "listening_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    position_seconds = Column(Integer, nullable=False, default=0)
    total_listened_seconds = Column(Integer, nullable=False, default=0)
    last_listened_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="_user_book_uc"),
        CheckConstraint("position_seconds >= 0", name="_position_nonnegative"),
        CheckConstraint("total_listened_seconds >= 0", name="_total_listened_nonnegative"),
    )
