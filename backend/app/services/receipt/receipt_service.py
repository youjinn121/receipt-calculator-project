import os
import shutil
from sqlalchemy.orm import Session, selectinload

from backend.app.models.receipt.receipt import Receipt
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

def now_kst_naive() -> datetime:
    return datetime.now(KST).replace(tzinfo=None)

UPLOAD_ROOT = "backend/storage/receipts"

def delete_receipt(db: Session, receipt_id: int) -> None:
    receipt = (
        db.query(Receipt)
        .options(
            selectinload(Receipt.images),
            selectinload(Receipt.items),
            selectinload(Receipt.lines),
            selectinload(Receipt.validation),
            selectinload(Receipt.analysis),
        )
        .filter(Receipt.id == receipt_id)
        .first()
    )

    if not receipt:
        raise ValueError("영수증을 찾을 수 없습니다.")

    receipt_dir = os.path.join(UPLOAD_ROOT, str(receipt_id))

    if os.path.exists(receipt_dir):
        shutil.rmtree(receipt_dir)

    db.delete(receipt)
    db.commit()

def create_receipt(db: Session, file_name: str) -> Receipt:
    receipt = Receipt(
        file_name=file_name,
        status="uploaded",
        analyzed_at=now_kst_naive(),
    )
    db.add(receipt)
    db.flush()
    return receipt


def update_receipt_store(db: Session, receipt_id: int, store: str) -> Receipt:
    receipt = (
        db.query(Receipt)
        .filter(Receipt.id == receipt_id)
        .first()
    )

    if not receipt:
        raise ValueError("영수증을 찾을 수 없습니다.")

    receipt.store = store
    receipt.status = "store_selected"

    db.add(receipt)
    db.commit()
    db.refresh(receipt)

    return receipt

def get_receipt_detail(db: Session, receipt_id: int) -> Receipt:
    receipt = (
        db.query(Receipt)
        .options(
            selectinload(Receipt.items),
            selectinload(Receipt.validation),
            selectinload(Receipt.analysis),
        )
        .filter(Receipt.id == receipt_id)
        .first()
    )

    if not receipt:
        raise ValueError("영수증을 찾을 수 없습니다.")

    return receipt


def get_completed_receipts(db: Session) -> list[Receipt]:
    return (
        db.query(Receipt)
        .options(
            selectinload(Receipt.items),
            selectinload(Receipt.validation),
            selectinload(Receipt.analysis),
        )
        .filter(
            Receipt.status == "pipeline_completed",
            Receipt.is_valid == True,
            Receipt.recapture_recommended == False,
        )
        .order_by(Receipt.analyzed_at.desc())
        .all()
    )