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

    # 간식 소비 지수 = (간식 + 주류 + 음료) / 전체
    guilty_pleasure_index = Column(Float, nullable=True)

    # 홈쿠킹 성향 지수 = 식재료 / (식재료 + 간편식)
    home_cooking_independence = Column(Float, nullable=True)

    # 간식 + 주류 + 음료 금액
    guilty_pleasure_amount = Column(Integer, nullable=True)

    # 식재료 금액
    home_food_amount = Column(Integer, nullable=True)

    # 전체 최종 금액
    total_final_price = Column(Integer, nullable=True)

    impulse_buy_factor = Column(Float, nullable=True)
    basket_variety_score = Column(Float, nullable=True)

    receipt = relationship("Receipt", back_populates="analysis")