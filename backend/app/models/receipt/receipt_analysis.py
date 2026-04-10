from sqlalchemy import Column, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship

from backend.app.db.base_class import Base


class ReceiptAnalysis(Base):
    __tablename__ = "receipt_analysis"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(
        Integer,
        ForeignKey("receipts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    guilty_pleasure_index = Column(Float, nullable=True)
    home_cooking_ratio = Column(Float, nullable=True)
    impulse_buy_factor = Column(Float, nullable=True)
    basket_variety_score = Column(Float, nullable=True)

    receipt = relationship("Receipt", back_populates="analysis")