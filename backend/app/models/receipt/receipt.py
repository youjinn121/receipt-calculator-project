from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False)
    store = Column(String, nullable=True)

    item_total = Column(Integer, nullable=True)
    payment_total = Column(Integer, nullable=True)
    receipt_discount_total = Column(Integer, nullable=True)
    fee_total = Column(Integer, nullable=True)

    is_valid = Column(Boolean, nullable=False, default=False)
    is_total_inferred = Column(Boolean, nullable=False, default=False)
    requires_user_total_confirmation = Column(Boolean, nullable=False, default=False)

    status = Column(String, nullable=False, default="uploaded")

    # 1:N
    images = relationship(
        "ReceiptImage",
        back_populates="receipt",
        cascade="all, delete-orphan",
    )
    items = relationship(
        "ReceiptItem",
        back_populates="receipt",
        cascade="all, delete-orphan",
    )
    lines = relationship(
        "ReceiptLine",
        back_populates="receipt",
        cascade="all, delete-orphan",
    )

    # 1:1
    validation = relationship(
        "ReceiptValidation",
        back_populates="receipt",
        uselist=False,
        cascade="all, delete-orphan",
    )
    analysis = relationship(
        "ReceiptAnalysis",
        back_populates="receipt",
        uselist=False,
        cascade="all, delete-orphan",
    )