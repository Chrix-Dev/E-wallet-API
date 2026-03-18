import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    response_snapshot = Column(Text, nullable=False)  # stores the response as a JSON string
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))