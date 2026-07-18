from sqlalchemy import Column, String, Boolean, DateTime, func, UniqueConstraint, CheckConstraint, ForeignKey, SmallInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import expression
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(320), unique=True, nullable=True)
    display_name = Column(String(150), nullable=False)
    avatar_url = Column(String(2048), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("display_name != ''", name="_display_name_not_empty"),
    )

    auth_providers = relationship("AuthProvider", back_populates="user", cascade="all, delete-orphan")


class UserMonthlyLimit(Base):
    __tablename__ = "user_monthly_limits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    year = Column("year", SmallInteger, nullable=False)
    month = Column("month", SmallInteger, nullable=False)
    conversions_used = Column(SmallInteger, nullable=False, default=0)
    conversions_limit = Column(SmallInteger, nullable=False, default=3)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "year", "month", name="_user_year_month_uc"),
        CheckConstraint("month BETWEEN 1 AND 12", name="_month_range_check"),
        CheckConstraint("conversions_used >= 0", name="_conversions_used_nonnegative"),
        CheckConstraint("conversions_limit > 0", name="_conversions_limit_positive"),
        CheckConstraint("conversions_used <= conversions_limit", name="chk_conversions_not_exceeded"),
    )
