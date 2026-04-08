from sqlalchemy.orm import declarative_base

Base = declarative_base()

# 모델 import 등록
from backend.app.models.receipt.receipt import Receipt
from backend.app.models.receipt.receipt_image import ReceiptImage
from backend.app.models.receipt.receipt_item import ReceiptItem
from backend.app.models.receipt.receipt_validation import ReceiptValidation
from backend.app.models.receipt.receipt_analysis import ReceiptAnalysis
from backend.app.models.receipt.receipt_line import ReceiptLine

__all__ = [
    "Base",
    "Receipt",
    "ReceiptImage",
    "ReceiptItem",
    "ReceiptValidation",
    "ReceiptAnalysis",
    "ReceiptLine",
]