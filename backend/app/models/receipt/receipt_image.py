from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


class ReceiptImage(Base):
    __tablename__ = "receipt_images"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False)
    page_no = Column(Integer, nullable=False)
    file_path = Column(String, nullable=False)

    receipt = relationship("Receipt", back_populates="images")