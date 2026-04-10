from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.app.db.base_class import Base


class ReceiptLine(Base):
    __tablename__ = "receipt_lines"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False)

    line_idx = Column(Integer, nullable=False)
    line_text = Column(Text, nullable=False)
    normalized_line_text = Column(Text, nullable=True)
    line_type = Column(String, nullable=True)

    price_raw = Column(Integer, nullable=True)
    name_raw = Column(String, nullable=True)
    is_restored = Column(Boolean, nullable=True)
    restore_reason = Column(Text, nullable=True)

    receipt = relationship("Receipt", back_populates="lines")