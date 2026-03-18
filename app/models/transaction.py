import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base 


class TransactionType(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    TRANSFER = "transfer"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference = Column(String(100), unique=True, nullable=False, index=True)
    type = Column(SAEnum(TransactionType), nullable=False)
    status = Column(SAEnum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False)
    amount = Column(Numeric(20, 2), nullable=False)
    fee = Column(Numeric(20, 2), default=Decimal("0.00"), nullable=False)
    sender_wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="SET NULL"), nullable=True)
    receiver_wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="SET NULL"), nullable=True)
    narration = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    sender_wallet = relationship("Wallet", foreign_keys=[sender_wallet_id], back_populates="sent_transactions")
    receiver_wallet = relationship("Wallet", foreign_keys=[receiver_wallet_id], back_populates="received_transactions")