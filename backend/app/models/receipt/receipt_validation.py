from sqlalchemy import Column, Float, ForeignKey, Integer, Boolean
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


class ReceiptValidation(Base):
    __tablename__ = "receipt_validation"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(
        Integer,
        ForeignKey("receipts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    checked_item_count = Column(Integer, nullable=True)
    valid_item_count = Column(Integer, nullable=True)
    invalid_item_count = Column(Integer, nullable=True)

    total_match = Column(Boolean, nullable=True)
    subtotal_segment_match = Column(Boolean, nullable=True)
    categorization_rate = Column(Float, nullable=True)

    error_count = Column(Integer, nullable=True)
    warning_count = Column(Integer, nullable=True)

    receipt = relationship("Receipt", back_populates="validation")