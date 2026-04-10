from sqlalchemy.orm import Session, selectinload

from backend.app.models.receipt.receipt import Receipt
from backend.app.services.receipt.ocr_service import run_ocr_for_image


def run_ocr_pipeline(db: Session, receipt_id: int) -> Receipt:
    receipt = (
        db.query(Receipt)
        .options(selectinload(Receipt.images))
        .filter(Receipt.id == receipt_id)
        .first()
    )

    if not receipt:
        raise ValueError("영수증을 찾을 수 없습니다.")

    if not receipt.images:
        raise ValueError("처리할 영수증 이미지가 없습니다.")

    receipt.status = "ocr_processing"
    db.add(receipt)
    db.commit()
    db.refresh(receipt)

    try:
        for image in receipt.images:
            json_path = run_ocr_for_image(image.file_path)
            image.ocr_json_path = json_path
            db.add(image)

        receipt.status = "ocr_completed"
        db.add(receipt)
        db.commit()
        db.refresh(receipt)
        return receipt

    except Exception:
        receipt.status = "failed"
        db.add(receipt)
        db.commit()
        raise