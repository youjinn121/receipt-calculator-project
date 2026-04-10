import json

from sqlalchemy.orm import Session, selectinload

from backend.app.models.receipt.receipt import Receipt
from backend.app.models.receipt.receipt_item import ReceiptItem
from backend.app.models.receipt.receipt_line import ReceiptLine
from backend.app.models.receipt.receipt_validation import ReceiptValidation
from parser import run_line_sorting_for_single_receipt_pages
from run_pipeline import run_receipt_pipeline


def _clear_previous_pipeline_result(db: Session, receipt: Receipt) -> None:
    db.query(ReceiptLine).filter(ReceiptLine.receipt_id == receipt.id).delete()
    db.query(ReceiptItem).filter(ReceiptItem.receipt_id == receipt.id).delete()
    db.query(ReceiptValidation).filter(ReceiptValidation.receipt_id == receipt.id).delete()
    db.flush()


def _update_receipt_row(
    receipt: Receipt,
    parsed_result: dict,
    semantic_result: dict,
    validation_result: dict,
) -> None:
    receipt_summary = semantic_result.get("receipt") or {}
    if not receipt_summary:
        receipt_summary = (semantic_result.get("tail_info") or {}).get("summary", {})

    debug_receipt = (validation_result.get("debug") or {}).get("receipt_validation", {})

    receipt.file_name = parsed_result.get("file_name") or receipt.file_name
    receipt.store = semantic_result.get("store") or receipt.store

    receipt.item_total = receipt_summary.get("item_total")
    receipt.payment_total = receipt_summary.get("payment_total")
    receipt.receipt_discount_total = receipt_summary.get("receipt_discount_total")
    receipt.fee_total = receipt_summary.get("fee_total")

    receipt.is_valid = validation_result.get("is_valid", False)
    receipt.is_total_inferred = debug_receipt.get("is_total_inferred", False)
    receipt.requires_user_total_confirmation = debug_receipt.get(
        "requires_user_total_confirmation",
        False,
    )

    receipt.status = "pipeline_completed"


def _save_receipt_lines(db: Session, receipt_id: int, parsed_result: dict) -> None:
    for line in parsed_result.get("lines", []):
        row = ReceiptLine(
            receipt_id=receipt_id,
            line_idx=line.get("line_idx"),
            line_text=line.get("line_text", ""),
            normalized_line_text=line.get("normalized_line_text"),
            line_type=line.get("line_type"),
            price_raw=line.get("price_raw"),
            name_raw=line.get("name_raw"),
            is_restored=line.get("is_restored"),
            restore_reason=line.get("restore_reason"),
        )
        db.add(row)


def _save_receipt_items(db: Session, receipt_id: int, semantic_result: dict) -> None:
    for item in semantic_result.get("items", []):
        row = ReceiptItem(
            receipt_id=receipt_id,
            name=item.get("name") or "",
            normalized_name=item.get("normalized_name"),
            category=item.get("category"),
            category_source=item.get("category_source"),
            code=item.get("code"),
            qty=item.get("qty"),
            unit_price=item.get("unit_price"),
            base_price=item.get("base_price"),
            discount=item.get("discount"),
            final_price=item.get("final_price"),
            source_line_indices=item.get("source_line_indices"),
        )
        db.add(row)


def _save_receipt_validation(
    db: Session,
    receipt_id: int,
    semantic_result: dict,
    validation_result: dict,
) -> None:
    category_summary = (semantic_result.get("analysis") or {}).get("category_summary", {})
    item_validation = validation_result.get("item_validation", {})
    receipt_validation = validation_result.get("receipt_validation", {})

    row = ReceiptValidation(
        receipt_id=receipt_id,
        checked_item_count=item_validation.get("checked_item_count"),
        valid_item_count=item_validation.get("valid_item_count"),
        invalid_item_count=item_validation.get("invalid_item_count"),
        total_match=receipt_validation.get("total_match"),
        subtotal_segment_match=receipt_validation.get("subtotal_segment_match"),
        categorization_rate=category_summary.get("categorization_rate"),
        error_count=len(validation_result.get("errors", [])),
        warning_count=len(validation_result.get("warnings", [])),
    )
    db.add(row)


def run_pipeline_for_receipt(db: Session, receipt_id: int) -> dict:
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

    if not receipt.store:
        raise ValueError("마트 정보가 없습니다. 먼저 store를 선택하세요.")

    page_ocr_jsons = []
    sorted_images = sorted(receipt.images, key=lambda image: image.page_no)

    for image in sorted_images:
        if not image.ocr_json_path:
            raise ValueError(
                f"{image.page_no}번 이미지의 OCR 결과가 없습니다. 먼저 OCR을 실행하세요."
            )

        try:
            with open(image.ocr_json_path, "r", encoding="utf-8") as f:
                ocr_data = json.load(f)
        except FileNotFoundError:
            raise ValueError(
                f"OCR json 파일이 존재하지 않습니다: {image.ocr_json_path}"
            )

        page_ocr_jsons.append(
            {
                "page_no": image.page_no,
                "ocr_data": ocr_data,
            }
        )

    line_sorted_result = run_line_sorting_for_single_receipt_pages(
        page_ocr_jsons=page_ocr_jsons,
        receipt_file_name=f"receipt_{receipt.id}.json",
    )

    pipeline_result = run_receipt_pipeline(
        receipt=line_sorted_result,
        store=receipt.store,
    )

    parsed_result = pipeline_result["parsed"]
    semantic_result = pipeline_result["semantic"]
    validation_result = pipeline_result["validation"]

    _clear_previous_pipeline_result(db=db, receipt=receipt)

    _update_receipt_row(
        receipt=receipt,
        parsed_result=parsed_result,
        semantic_result=semantic_result,
        validation_result=validation_result,
    )

    _save_receipt_lines(
        db=db,
        receipt_id=receipt.id,
        parsed_result=parsed_result,
    )

    _save_receipt_items(
        db=db,
        receipt_id=receipt.id,
        semantic_result=semantic_result,
    )

    _save_receipt_validation(
        db=db,
        receipt_id=receipt.id,
        semantic_result=semantic_result,
        validation_result=validation_result,
    )

    db.add(receipt)
    db.commit()
    db.refresh(receipt)

    return {
        "receipt_id": receipt.id,
        "status": receipt.status,
        "file_name": parsed_result.get("file_name"),
        "file_meta": parsed_result.get("file_meta", {}),
        "line_count": len(parsed_result.get("lines", [])),
        "lines": parsed_result.get("lines", []),
        "semantic": semantic_result,
        "validation": validation_result,
    }