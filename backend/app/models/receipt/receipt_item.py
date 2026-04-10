from sqlalchemy import Column, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


class ReceiptItem(Base):
    __tablename__ = "receipt_items"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False)

    name = Column(String, nullable=False)
    normalized_name = Column(String, nullable=True)
    category = Column(String, nullable=True)
    category_source = Column(String, nullable=True)

    code = Column(String, nullable=True)
    qty = Column(Integer, nullable=True)
    unit_price = Column(Integer, nullable=True)
    base_price = Column(Integer, nullable=True)
    discount = Column(Integer, nullable=True)
    final_price = Column(Integer, nullable=True)

    source_line_indices = Column(JSON, nullable=True)

    receipt = relationship("Receipt", back_populates="items")