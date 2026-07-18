from sqlalchemy import Column, String, Boolean, DateTime, func, UniqueConstraint, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base
from app.shared.enums import AuthProviderType


class AuthProvider(Base):
    __tablename__ = "auth_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(Enum(AuthProviderType, name="auth_provider_type"), nullable=False)
    provider_user_id = Column(String(256), nullable=True)
    provider_email = Column(String(320), nullable=False)
    password_hash = Column(String(256), nullable=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="_user_provider_uc"),
        UniqueConstraint("provider", "provider_user_id", name="_provider_user_id_uc"),
        UniqueConstraint("provider", "provider_email", name="_provider_email_uc"),
    )

    user = relationship("User", back_populates="auth_providers")
