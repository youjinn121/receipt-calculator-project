from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.app.db.base_class import Base


class ReceiptItemCategory(Base):
    __tablename__ = "receipt_item_categories"

    id = Column(Integer, primary_key=True, index=True)

    receipt_item_id = Column(
        Integer,
        ForeignKey("receipt_items.id", ondelete="CASCADE"),
        nullable=False,
    )

    name = Column(String, nullable=False)

    category = Column(String, nullable=False)

    category_source = Column(String, nullable=True)

    raw_response = Column(Text, nullable=True)

    use_fallback = Column(Boolean, default=False)

    use_llm = Column(Boolean, default=True)

    use_cache = Column(Boolean, default=True)

    cache_hit = Column(Boolean, default=False)

    receipt_item = relationship("ReceiptItem")