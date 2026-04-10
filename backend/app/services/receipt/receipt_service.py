from sqlalchemy.orm import Session

from backend.app.models.receipt.receipt import Receipt


def create_receipt(db: Session, file_name: str) -> Receipt:
    receipt = Receipt(
        file_name=file_name,
        status="uploaded",
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