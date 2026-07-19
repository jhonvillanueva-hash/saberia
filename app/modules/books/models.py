from sqlalchemy import Column, String, Boolean, DateTime, Integer, BigInteger, Text, func, CheckConstraint, UniqueConstraint, ForeignKey, Enum, SmallInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import expression
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base
from app.shared.enums import BookStatus, BookFileType, ChapterAudioStatus, AudioFileStatus


class Book(Base):
    __tablename__ = "books"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    title = Column(String(512), nullable=False)
    author = Column(String(512), nullable=True)
    language = Column(String(10), nullable=True)
    original_filename = Column(String(512), nullable=False)
    cover_r2_path = Column(String(2048), nullable=True)
    original_file_r2_path = Column(String(2048), nullable=False)
    file_type = Column(Enum(BookFileType, name="book_file_type"), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    page_count = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)
    chapter_count = Column(Integer, nullable=False, default=0)
    total_duration_seconds = Column(Integer, nullable=True)
    status = Column(Enum(BookStatus, name="book_status"), nullable=False, default="pending")
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="books")

    __table_args__ = (
        CheckConstraint(
            "(file_type != 'pdf'::book_file_type) OR (file_size_bytes <= 52428800)",
            name="chk_pdf_size"
        ),
        CheckConstraint(
            "(file_type != 'epub'::book_file_type) OR (file_size_bytes <= 20971520)",
            name="chk_epub_size"
        ),
        CheckConstraint("page_count IS NULL OR (page_count BETWEEN 1 AND 300)", name="_page_count_range"),
        CheckConstraint("word_count IS NULL OR (word_count BETWEEN 1 AND 100000)", name="_word_count_range"),
        CheckConstraint("chapter_count >= 0", name="_chapter_count_nonnegative"),
        CheckConstraint("total_duration_seconds IS NULL OR total_duration_seconds > 0", name="_duration_positive"),
        CheckConstraint("file_size_bytes > 0", name="_file_size_positive"),
    )


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False, unique=True)
    status = Column(Enum(BookStatus, name="book_status"), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("retry_count >= 0", name="_retry_count_nonnegative"),
    )


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    chapter_number = Column("chapter_number", SmallInteger, nullable=False)
    title = Column(String(512), nullable=True)
    order_index = Column("order_index", SmallInteger, nullable=False)
    extracted_text = Column(Text, nullable=False)
    word_count = Column(Integer, nullable=False, default=0)
    estimated_duration_seconds = Column(Integer, nullable=True)
    audio_status = Column("audio_status", Enum(ChapterAudioStatus, name="chapter_audio_status"), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("book_id", "order_index", name="_book_order_uc"),
        CheckConstraint("chapter_number >= 0", name="_chapter_number_nonnegative"),
        CheckConstraint("order_index >= 1", name="_order_index_positive"),
        CheckConstraint("word_count >= 0", name="_word_count_nonnegative"),
        CheckConstraint("estimated_duration_seconds IS NULL OR estimated_duration_seconds > 0", name="_duration_positive"),
    )


class ChapterAudio(Base):
    __tablename__ = "chapter_audios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, unique=True)
    r2_path = Column(String(2048), nullable=False)
    language = Column(String(10), nullable=True)
    duration_seconds = Column(Integer, nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    status = Column("status", Enum(AudioFileStatus, name="audio_file_status"), nullable=False, default="active")
    tts_voice_id = Column(String(128), nullable=True)
    tts_model = Column(String(128), nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("duration_seconds > 0", name="_duration_positive"),
        CheckConstraint("file_size_bytes > 0", name="_file_size_positive"),
    )
