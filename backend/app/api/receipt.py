from typing import List

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from backend.app.controllers.receipt_controller import (
    get_receipt_detail_controller,
    run_ocr_controller,
    run_parser_controller,
    update_receipt_store_controller,
    upload_receipt_controller,
    delete_receipt_controller,
    update_receipt_item_categories_controller,
    get_completed_receipts_controller,
)

from backend.app.db.database import get_db
from backend.app.schemas.receipt import (
    ReceiptDetailResponse,
    ReceiptOcrResponse,
    ReceiptParserResponse,
    ReceiptStoreUpdateRequest,
    ReceiptStoreUpdateResponse,
    ReceiptUploadResponse,
    ReceiptItemCategoryBulkUpdateRequest,
    ReceiptItemCategoryBulkUpdateResponse,
)

router = APIRouter(prefix="/receipts", tags=["receipts"])

@router.get("")
def get_completed_receipts(
    db: Session = Depends(get_db),
):
    return get_completed_receipts_controller(db=db)

@router.post("/upload", response_model=ReceiptUploadResponse)
async def upload_receipt(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    return await upload_receipt_controller(db=db, files=files)


@router.patch(
    "/{receipt_id}/items/categories",
    response_model=ReceiptItemCategoryBulkUpdateResponse,
)
def update_receipt_item_categories(
    receipt_id: int,
    request: ReceiptItemCategoryBulkUpdateRequest,
    db: Session = Depends(get_db),
):
    return update_receipt_item_categories_controller(
        db=db,
        receipt_id=receipt_id,
        request=request,
    )

@router.get("/{receipt_id}", response_model=ReceiptDetailResponse)
def get_receipt_detail(
    receipt_id: int,
    db: Session = Depends(get_db),
):
    return get_receipt_detail_controller(
        db=db,
        receipt_id=receipt_id,
    )


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


@router.delete("/{receipt_id}")
def delete_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
):
    return delete_receipt_controller(
        db=db,
        receipt_id=receipt_id,
    )