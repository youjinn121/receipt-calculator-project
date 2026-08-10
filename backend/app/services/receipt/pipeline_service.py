import json
import os
from typing import Any, Dict

from sqlalchemy.orm import Session, selectinload

from backend.app.models.receipt.receipt import Receipt
from backend.app.models.receipt.receipt_item import ReceiptItem
from backend.app.models.receipt.receipt_line import ReceiptLine
from backend.app.models.receipt.receipt_validation import ReceiptValidation
from ocr_preprocess.line_sorting import run_line_sorting_for_single_receipt_pages
from pipeline_runner import run_receipt_pipeline
from llm.category_manager import categorize_receipt_items
from backend.app.models.receipt.receipt_analysis import ReceiptAnalysis
from backend.app.models.receipt.receipt_item_category import ReceiptItemCategory

def _build_empty_analysis() -> Dict[str, Any]:
    return {
        "category_summary": {
            "categorized_item_count": None,
            "uncategorized_item_count": None,
            "categorization_rate": None,
        },
        "basket_metrics": {
            "guilty_pleasure_index": None,
            "home_cooking_ratio": None,
            "impulse_buy_factor": None,
            "basket_variety_score": None,
        },
    }


def _build_receipt_summary(
    semantic_result: Dict[str, Any],
    validation_result: Dict[str, Any],
) -> Dict[str, Any]:
    tail_summary = (semantic_result.get("tail_info") or {}).get("summary", {}) or {}
    debug_receipt = (validation_result.get("debug") or {}).get("receipt_validation", {}) or {}

    item_total = tail_summary.get("item_total")
    payment_total = tail_summary.get("payment_total")

    if item_total is None:
        item_total = debug_receipt.get("item_total")

    if payment_total is None:
        payment_total = (
            debug_receipt.get("payment_total")
            or debug_receipt.get("receipt_total")
            or validation_result.get("inferred_total")
        )

    return {
        "item_total": item_total,
        "payment_total": payment_total,
        "receipt_discount_total": tail_summary.get("receipt_discount_total"),
        "fee_total": tail_summary.get("fee_total"),
        "is_total_inferred": validation_result.get(
            "is_total_inferred",
            debug_receipt.get("is_total_inferred", False),
        ),
        "inferred_total": validation_result.get(
            "inferred_total",
            debug_receipt.get("inferred_total"),
        ),
        "inferred_total_source": validation_result.get(
            "inferred_total_source",
            debug_receipt.get("inferred_total_source"),
        ),
        "requires_user_total_confirmation": validation_result.get(
            "requires_user_total_confirmation",
            debug_receipt.get("requires_user_total_confirmation", False),
        ),
    }


def _build_final_output(
    *,
    parsed_result: Dict[str, Any],
    semantic_result: Dict[str, Any],
    validation_result: Dict[str, Any],
) -> Dict[str, Any]:
    analysis = semantic_result.get("analysis")
    if not isinstance(analysis, dict):
        analysis = _build_empty_analysis()
    else:
        analysis = {
            "category_summary": {
                "categorized_item_count": (analysis.get("category_summary") or {}).get("categorized_item_count"),
                "uncategorized_item_count": (analysis.get("category_summary") or {}).get("uncategorized_item_count"),
                "categorization_rate": (analysis.get("category_summary") or {}).get("categorization_rate"),
            },
            "basket_metrics": {
                "guilty_pleasure_index": (analysis.get("basket_metrics") or {}).get("guilty_pleasure_index"),
                "home_cooking_ratio": (analysis.get("basket_metrics") or {}).get("home_cooking_ratio"),
                "impulse_buy_factor": (analysis.get("basket_metrics") or {}).get("impulse_buy_factor"),
                "basket_variety_score": (analysis.get("basket_metrics") or {}).get("basket_variety_score"),
            },
        }

    return {
        "file_name": parsed_result.get("file_name", ""),
        "file_meta": parsed_result.get("file_meta", {}),
        "store": semantic_result.get("store") or parsed_result.get("store", ""),
        "receipt": _build_receipt_summary(
            semantic_result=semantic_result,
            validation_result=validation_result,
        ),
        "items": semantic_result.get("items", []),
        "tail_info": semantic_result.get("tail_info", {}),
        "validation": validation_result,
        "lines": parsed_result.get("lines", []),
        "analysis": analysis,
    }


def _build_final_output_path(receipt_id: int) -> str:
    return os.path.join(
        "backend",
        "storage",
        "receipts",
        str(receipt_id),
        "final_output.json",
    )


def _save_final_output_json(receipt_id: int, final_output: Dict[str, Any]) -> str:
    output_path = _build_final_output_path(receipt_id)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)

    return output_path


def _clear_previous_pipeline_result(db: Session, receipt: Receipt) -> None:
    db.query(ReceiptLine).filter(ReceiptLine.receipt_id == receipt.id).delete()
    db.query(ReceiptItem).filter(ReceiptItem.receipt_id == receipt.id).delete()
    db.query(ReceiptValidation).filter(ReceiptValidation.receipt_id == receipt.id).delete()
    db.query(ReceiptAnalysis).filter(ReceiptAnalysis.receipt_id == receipt.id).delete()
    db.flush()
    db.query(ReceiptLine).filter(ReceiptLine.receipt_id == receipt.id).delete()
    db.query(ReceiptItem).filter(ReceiptItem.receipt_id == receipt.id).delete()
    db.query(ReceiptValidation).filter(ReceiptValidation.receipt_id == receipt.id).delete()
    db.flush()


def _update_receipt_row(
    receipt: Receipt,
    final_output: dict,
) -> None:
    receipt_summary = final_output.get("receipt", {})
    validation = final_output.get("validation", {})

    receipt.file_name = final_output.get("file_name") or receipt.file_name
    receipt.store = final_output.get("store") or receipt.store

    receipt.item_total = receipt_summary.get("item_total")
    receipt.payment_total = receipt_summary.get("payment_total")
    receipt.receipt_discount_total = receipt_summary.get("receipt_discount_total")
    receipt.fee_total = receipt_summary.get("fee_total")

    receipt.is_valid = validation.get("is_valid", False)
    receipt.recapture_recommended = validation.get("recapture_recommended", False)
    receipt.is_total_inferred = receipt_summary.get("is_total_inferred", False)
    receipt.requires_user_total_confirmation = receipt_summary.get(
        "requires_user_total_confirmation",
        False,
    )

    receipt.status = "pipeline_completed"


def _save_receipt_lines(db: Session, receipt_id: int, final_output: dict) -> None:
    for line in final_output.get("lines", []):
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


def _save_receipt_items(db: Session, receipt_id: int, final_output: dict) -> None:
    for item in final_output.get("items", []):
        category_meta = item.get("category_meta") or {}

        row = ReceiptItem(
            receipt_id=receipt_id,
            name=item.get("name") or "",
            normalized_name=item.get("normalized_name"),
            category=item.get("category"),
            category_source=(
                item.get("category_source")
                or category_meta.get("method")
            ),
            code=item.get("code"),
            qty=item.get("qty"),
            unit_price=item.get("unit_price"),
            base_price=item.get("base_price"),
            discount=item.get("discount"),
            final_price=item.get("final_price"),
            source_line_indices=item.get("source_line_indices"),
        )

        db.add(row)
        db.flush()

        category_row = ReceiptItemCategory(
            receipt_item_id=row.id,
            name=item.get("name") or "",
            category=item.get("category") or "Uncategorized",
            category_source=category_meta.get("method"),
            raw_response=category_meta.get("raw_response"),
            use_fallback=category_meta.get("use_fallback", False),
            use_llm=category_meta.get("use_llm", True),
            use_cache=category_meta.get("use_cache", True),
            cache_hit=category_meta.get("cache_hit", False),
        )

        db.add(category_row)


def _save_receipt_validation(
    db: Session,
    receipt_id: int,
    final_output: dict,
) -> None:
    validation = final_output.get("validation", {})
    item_validation = validation.get("item_validation", {})
    receipt_validation = validation.get("receipt_validation", {})
    category_summary = (final_output.get("analysis") or {}).get("category_summary", {})

    row = ReceiptValidation(
        receipt_id=receipt_id,
        checked_item_count=item_validation.get("checked_item_count"),
        valid_item_count=item_validation.get("valid_item_count"),
        invalid_item_count=item_validation.get("invalid_item_count"),
        total_match=receipt_validation.get("total_match"),
        subtotal_segment_match=receipt_validation.get("subtotal_segment_match"),
        categorization_rate=category_summary.get("categorization_rate"),
        error_count=len(validation.get("errors", [])),
        warning_count=len(validation.get("warnings", [])),
    )
    db.add(row)

def _save_receipt_analysis(
    db: Session,
    receipt_id: int,
    final_output: dict,
) -> None:
    items = final_output.get("items", [])

    snack_categories = {"간식", "주류", "음료"}
    home_food_categories = {"식재료"}
    convenience_categories = {"간편식"}

    guilty_pleasure_amount = 0
    home_food_amount = 0
    convenience_food_amount = 0
    total_final_price = 0

    for item in items:
        category = item.get("category")
        final_price = item.get("final_price") or 0

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

    home_cooking_denominator = home_food_amount + convenience_food_amount

    home_cooking_independence = (
        home_food_amount / home_cooking_denominator
        if home_cooking_denominator > 0
        else None
    )

    row = ReceiptAnalysis(
        receipt_id=receipt_id,
        guilty_pleasure_index=guilty_pleasure_index,
        home_cooking_independence=home_cooking_independence,
        guilty_pleasure_amount=guilty_pleasure_amount,
        home_food_amount=home_food_amount,
        total_final_price=total_final_price,
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
    
    categorized_result = categorize_receipt_items(
        semantic_receipt=semantic_result,
        model="gpt-4o-mini",
        use_llm=True,
        use_fallback=True,
        use_cache=True,
        save_cache=True,
    )
    
    semantic_result = categorized_result
    
    final_output = _build_final_output(
        parsed_result=parsed_result,
        semantic_result=semantic_result,
        validation_result=validation_result,
        )

    final_output_path = _save_final_output_json(
        receipt_id=receipt.id,
        final_output=final_output,
    )

    _clear_previous_pipeline_result(db=db, receipt=receipt)

    _update_receipt_row(
        receipt=receipt,
        final_output=final_output,
    )

    _save_receipt_lines(
        db=db,
        receipt_id=receipt.id,
        final_output=final_output,
    )

    _save_receipt_items(
        db=db,
        receipt_id=receipt.id,
        final_output=final_output,
    )

    _save_receipt_validation(
        db=db,
        receipt_id=receipt.id,
        final_output=final_output,
    )
    
    _save_receipt_analysis(
        db=db,
        receipt_id=receipt.id,
        final_output=final_output,
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