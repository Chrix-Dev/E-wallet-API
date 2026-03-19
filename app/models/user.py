import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String, nullable=True)
    google_id = Column(String(255), unique=True, nullable=True)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # tier system
    tier = Column(String(10), default="tier1", nullable=False)

    # tier 2 credentials
    phone_number = Column(String(20), nullable=True)
    date_of_birth = Column(String(20), nullable=True)
    bvn = Column(String(11), nullable=True)

    # tier 3credentials
    id_type = Column(String(50), nullable=True)  # NIN, passport, drivers_license
    id_number = Column(String(11), nullable=True)
    address = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    wallet = relationship("Wallet", back_populates="user", uselist=False)
    refresh_tokens = relationship("RefreshToken", back_populates="user")