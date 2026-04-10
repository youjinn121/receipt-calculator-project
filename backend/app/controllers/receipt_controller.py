from typing import List

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.constants.store import SUPPORTED_STORES
from backend.app.services.receipt.ocr_batch_service import run_ocr_pipeline
from backend.app.services.receipt.receipt_service import update_receipt_store
from backend.app.services.receipt.upload_service import save_uploaded_receipt_files
from backend.app.services.receipt.pipeline_service import run_pipeline_for_receipt


async def upload_receipt_controller(db: Session, files: List[UploadFile]):
    result = await save_uploaded_receipt_files(db=db, files=files)
    return {
        "message": "영수증이 업로드되었습니다.",
        "data": result,
    }


def run_ocr_controller(db: Session, receipt_id: int):
    try:
        receipt = run_ocr_pipeline(db=db, receipt_id=receipt_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR 처리 중 오류가 발생했습니다: {e}")

    return {
        "message": "OCR 처리가 완료되었습니다.",
        "data": {
            "receipt_id": receipt.id,
            "status": receipt.status,
            "image_count": len(receipt.images),
            "images": [
                {
                    "page_no": image.page_no,
                    "file_path": image.file_path,
                    "ocr_json_path": image.ocr_json_path,
                }
                for image in receipt.images
            ],
        },
    }


def update_receipt_store_controller(db: Session, receipt_id: int, store: str):
    normalized_store = store.strip().lower()

    if normalized_store not in SUPPORTED_STORES:
        raise HTTPException(status_code=400, detail="지원하지 않는 store입니다.")

    try:
        receipt = update_receipt_store(
            db=db,
            receipt_id=receipt_id,
            store=normalized_store,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "message": "마트명이 저장되었습니다.",
        "data": {
            "receipt_id": receipt.id,
            "store": receipt.store,
            "status": receipt.status,
        },
    }


def run_parser_controller(db: Session, receipt_id: int):
    try:
        result = run_pipeline_for_receipt(db=db, receipt_id=receipt_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline 처리 중 오류가 발생했습니다: {e}")

    return {
        "message": "Pipeline 처리가 완료되었습니다.",
        "data": result,
    }