from typing import List

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from backend.app.controllers.receipt_controller import (
    run_ocr_controller,
    run_parser_controller,
    update_receipt_store_controller,
    upload_receipt_controller,
)
from backend.app.db.database import get_db
from backend.app.schemas.receipt import (
    ReceiptOcrResponse,
    ReceiptParserResponse,
    ReceiptStoreUpdateRequest,
    ReceiptStoreUpdateResponse,
    ReceiptUploadResponse,
)

router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.post("/upload", response_model=ReceiptUploadResponse)
async def upload_receipt(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    return await upload_receipt_controller(db=db, files=files)


@router.post("/{receipt_id}/run-ocr", response_model=ReceiptOcrResponse)
def run_ocr(
    receipt_id: int,
    db: Session = Depends(get_db),
):
    return run_ocr_controller(db=db, receipt_id=receipt_id)


@router.post("/{receipt_id}/run-parser", response_model=ReceiptParserResponse)
def run_parser(
    receipt_id: int,
    db: Session = Depends(get_db),
):
    return run_parser_controller(db=db, receipt_id=receipt_id)


@router.patch("/{receipt_id}/store", response_model=ReceiptStoreUpdateResponse)
def update_receipt_store(
    receipt_id: int,
    payload: ReceiptStoreUpdateRequest,
    db: Session = Depends(get_db),
):
    return update_receipt_store_controller(
        db=db,
        receipt_id=receipt_id,
        store=payload.store,
    )