import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    balance = Column(Numeric(20, 2), default=Decimal("0.00"), nullable=False)
    account_number = Column(String(10), unique=True, nullable=False, index=True)
    currency = Column(String(3), default="NGN", nullable=False)
    is_active = Column(Boolean, default=True)

    # daily usage tracking
    daily_transfer_used = Column(Numeric(20, 2), default=Decimal("0.00"), nullable=False)
    daily_withdrawal_used = Column(Numeric(20, 2), default=Decimal("0.00"), nullable=False)
    last_daily_reset = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="wallet")
    sent_transactions = relationship("Transaction", foreign_keys="Transaction.sender_wallet_id", back_populates="sender_wallet")
    received_transactions = relationship("Transaction", foreign_keys="Transaction.receiver_wallet_id", back_populates="receiver_wallet")