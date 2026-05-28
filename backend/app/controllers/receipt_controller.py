from typing import List

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.constants.store import SUPPORTED_STORES
from backend.app.services.receipt.ocr_batch_service import run_ocr_pipeline
from backend.app.services.receipt.receipt_service import (
    get_receipt_detail,
    update_receipt_store,
    delete_receipt,
    get_completed_receipts,
)
from backend.app.services.receipt.upload_service import save_uploaded_receipt_files
from backend.app.services.receipt.pipeline_service import run_pipeline_for_receipt

from backend.app.models.receipt.receipt import Receipt
from backend.app.models.receipt.receipt_item import ReceiptItem
from backend.app.models.receipt.receipt_analysis import ReceiptAnalysis
from backend.app.schemas.receipt import ReceiptItemCategoryBulkUpdateRequest


def get_completed_receipts_controller(db: Session):
    receipts = get_completed_receipts(db=db)

    return {
        "message": "완료된 영수증 목록 조회가 완료되었습니다.",
        "data": [
            {
                "receipt_id": receipt.id,
                "file_name": receipt.file_name,
                "store": receipt.store,
                "status": receipt.status,
                "analyzed_at": receipt.analyzed_at.isoformat()
                if receipt.analyzed_at
                else None,
                "payment_total": receipt.payment_total,
                "is_valid": receipt.is_valid,
                "recapture_recommended": receipt.recapture_recommended,
            }
            for receipt in receipts
        ],
    }


def delete_receipt_controller(db: Session, receipt_id: int):
    try:
        delete_receipt(db=db, receipt_id=receipt_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "message": "영수증이 삭제되었습니다.",
        "data": {
            "receipt_id": receipt_id,
            "deleted": True,
        },
    }


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
        raise HTTPException(
            status_code=500,
            detail=f"OCR 처리 중 오류가 발생했습니다: {e}",
        )

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
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline 처리 중 오류가 발생했습니다: {e}",
        )

    return {
        "message": "Pipeline 처리가 완료되었습니다.",
        "data": result,
    }


def get_receipt_detail_controller(db: Session, receipt_id: int):
    try:
        receipt = get_receipt_detail(db=db, receipt_id=receipt_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    validation = receipt.validation
    analysis = receipt.analysis

    return {
        "message": "영수증 상세 조회가 완료되었습니다.",
        "data": {
            "receipt_id": receipt.id,
            "file_name": receipt.file_name,
            "store": receipt.store,
            "status": receipt.status,
            "analyzed_at": receipt.analyzed_at.isoformat()
            if receipt.analyzed_at
            else None,
            "item_total": receipt.item_total,
            "payment_total": receipt.payment_total,
            "receipt_discount_total": receipt.receipt_discount_total,
            "fee_total": receipt.fee_total,
            "is_valid": receipt.is_valid,
            "recapture_recommended": receipt.recapture_recommended,
            "is_total_inferred": receipt.is_total_inferred,
            "requires_user_total_confirmation": receipt.requires_user_total_confirmation,
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "normalized_name": item.normalized_name,
                    "category": item.category,
                    "category_source": item.category_source,
                    "code": item.code,
                    "qty": item.qty,
                    "unit_price": item.unit_price,
                    "base_price": item.base_price,
                    "discount": item.discount,
                    "final_price": item.final_price,
                }
                for item in receipt.items
            ],
            "validation": None
            if validation is None
            else {
                "checked_item_count": validation.checked_item_count,
                "valid_item_count": validation.valid_item_count,
                "invalid_item_count": validation.invalid_item_count,
                "total_match": validation.total_match,
                "subtotal_segment_match": validation.subtotal_segment_match,
                "categorization_rate": validation.categorization_rate,
                "error_count": validation.error_count,
                "warning_count": validation.warning_count,
            },
            "analysis": None
            if analysis is None
            else {
                "guilty_pleasure_index": analysis.guilty_pleasure_index,
                "home_cooking_independence": analysis.home_cooking_independence,
                "guilty_pleasure_amount": analysis.guilty_pleasure_amount,
                "home_food_amount": analysis.home_food_amount,
                "total_final_price": analysis.total_final_price,
            },
        },
    }


ALLOWED_CATEGORIES = {
    "식재료",
    "간편식",
    "간식",
    "음료",
    "주류",
    "생활용품",
    "반려동물",
    "기타",
    "Uncategorized",
}


def update_receipt_item_categories_controller(
    db: Session,
    receipt_id: int,
    request: ReceiptItemCategoryBulkUpdateRequest,
):
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()

    if not receipt:
        raise HTTPException(status_code=404, detail="영수증을 찾을 수 없습니다.")

    updated_count = 0

    for update_item in request.items:
        if update_item.category not in ALLOWED_CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail=f"허용되지 않은 카테고리입니다: {update_item.category}",
            )

        item = (
            db.query(ReceiptItem)
            .filter(
                ReceiptItem.id == update_item.item_id,
                ReceiptItem.receipt_id == receipt_id,
            )
            .first()
        )

        if item is None:
            continue

        item.category = update_item.category
        item.category_source = "user"
        updated_count += 1

    _recalculate_receipt_analysis(db=db, receipt_id=receipt_id)

    db.commit()

    return {
        "message": "상품 카테고리가 수정되었습니다.",
        "data": {
            "receipt_id": receipt_id,
            "updated_count": updated_count,
        },
    }


def _recalculate_receipt_analysis(db: Session, receipt_id: int) -> None:
    items = (
        db.query(ReceiptItem)
        .filter(ReceiptItem.receipt_id == receipt_id)
        .all()
    )

    snack_categories = {"간식", "주류", "음료"}
    home_food_categories = {"식재료"}
    convenience_categories = {"간편식"}

    guilty_pleasure_amount = 0
    home_food_amount = 0
    convenience_food_amount = 0
    total_final_price = 0

    for item in items:
        category = item.category or "Uncategorized"
        final_price = item.final_price or 0

        total_final_price += final_price

        if category in snack_categories:
            guilty_pleasure_amount += final_price

        if category in home_food_categories:
            home_food_amount += final_price

        if category in convenience_categories:
            convenience_food_amount += final_price

    guilty_pleasure_index = (
        guilty_pleasure_amount / total_final_price
        if total_final_price > 0
        else None
    )

    home_cooking_base = home_food_amount + convenience_food_amount

    home_cooking_independence = (
        home_food_amount / home_cooking_base
        if home_cooking_base > 0
        else None
    )

    analysis = (
        db.query(ReceiptAnalysis)
        .filter(ReceiptAnalysis.receipt_id == receipt_id)
        .first()
    )

    if analysis is None:
        analysis = ReceiptAnalysis(receipt_id=receipt_id)
        db.add(analysis)

    analysis.guilty_pleasure_index = guilty_pleasure_index
    analysis.home_cooking_independence = home_cooking_independence
    analysis.guilty_pleasure_amount = guilty_pleasure_amount
    analysis.home_food_amount = home_food_amount
    analysis.total_final_price = total_final_price