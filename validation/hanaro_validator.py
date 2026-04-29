"""
[Hanaro Validator]

하나로마트 semantic 결과 검증 담당.

검증:
1) item 단위
   - base_price - discount == final_price
   - unit_price * qty == base_price

2) receipt 단위
   - sum(item.base_price) == item_total(총구매액)
   - item_total - receipt_discount_total + fee_total == payment_total(내실금액)

주의:
- validation은 데이터 수정/보정하지 않음
- 실패 여부와 debug 정보만 반환
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def validate_hanaro(semantic_receipt: Dict[str, Any]) -> Dict[str, Any]:
    items = semantic_receipt.get("items", [])
    tail_info = semantic_receipt.get("tail_info", {})

    item_result = _validate_items(items)
    receipt_result = _validate_receipt_totals(
        items=items,
        tail_info=tail_info,
        lines=semantic_receipt.get("lines", []),
    )

    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    errors.extend(item_result["errors"])
    errors.extend(receipt_result["errors"])
    warnings.extend(item_result["warnings"])
    warnings.extend(receipt_result["warnings"])

    recapture_info = _build_recapture_decision(errors, warnings)

    return {
        "file_name": semantic_receipt.get("file_name", ""),
        "file_meta": semantic_receipt.get("file_meta", {}),
        "store": "hanaro",

        "is_total_inferred": receipt_result["is_total_inferred"],
        "inferred_total": receipt_result["inferred_total"],
        "inferred_total_source": receipt_result["inferred_total_source"],
        "requires_user_total_confirmation": receipt_result["requires_user_total_confirmation"],

        "is_valid": len(errors) == 0,
        "recapture_recommended": recapture_info["recapture_recommended"],
        "recapture_reasons": recapture_info["reasons"],

        "item_validation": {
            "checked_item_count": item_result["checked_item_count"],
            "valid_item_count": item_result["valid_item_count"],
            "invalid_item_count": item_result["invalid_item_count"],
        },

        "receipt_validation": {
            "total_match": receipt_result["payment_total_match"],
            "subtotal_segment_match": None,
        },

        "debug": {
            "receipt_validation": {
                "computed_base_price_sum": receipt_result["computed_base_price_sum"],
                "computed_final_price_sum": receipt_result["computed_final_price_sum"],
                "computed_receipt_discount_sum": receipt_result["computed_receipt_discount_sum"],
                "computed_fee_sum": receipt_result["computed_fee_sum"],
                "computed_expected_payment_total": receipt_result["computed_expected_payment_total"],

                "item_total": receipt_result["item_total"],
                "payment_total": receipt_result["payment_total"],
                "receipt_total": receipt_result["payment_total"],
                "receipt_total_source": receipt_result["receipt_total_source"],

                "item_total_match": receipt_result["item_total_match"],
                "payment_total_match": receipt_result["payment_total_match"],

                "item_count": receipt_result["item_count"],
                "item_qty_sum": receipt_result["item_qty_sum"],
                "receipt_qty": receipt_result["receipt_qty"],
                "qty_match": receipt_result["qty_match"],

                "is_total_inferred": receipt_result["is_total_inferred"],
                "inferred_total": receipt_result["inferred_total"],
                "inferred_total_source": receipt_result["inferred_total_source"],
                "requires_user_total_confirmation": receipt_result["requires_user_total_confirmation"],
            },
            "subtotal_segment_results": [],
            "recapture_decision": {
                "trigger_count": recapture_info["trigger_count"],
                "reasons": recapture_info["reasons"],
            },
        },

        "errors": errors,
        "warnings": warnings,
    }


def _validate_items(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    checked_item_count = 0
    valid_item_count = 0
    invalid_item_count = 0

    for idx, item in enumerate(items):
        checked_item_count += 1

        name = item.get("name")
        base_price = item.get("base_price")
        discount = item.get("discount", 0) or 0
        final_price = item.get("final_price")
        unit_price = item.get("unit_price")
        qty = item.get("qty")

        if base_price is None or final_price is None:
            invalid_item_count += 1
            errors.append({
                "level": "item",
                "item_index": idx,
                "name": name,
                "reason": "base_price 또는 final_price가 없습니다.",
                "item": item,
            })
            continue

        expected_final = base_price - discount

        if expected_final != final_price:
            invalid_item_count += 1
            errors.append({
                "level": "item",
                "item_index": idx,
                "name": name,
                "reason": "base_price - discount != final_price",
                "expected_final_price": expected_final,
                "actual_final_price": final_price,
                "item": item,
            })
            continue

        if (
            isinstance(unit_price, int)
            and isinstance(qty, int)
            and isinstance(base_price, int)
        ):
            expected_base = unit_price * qty
            if expected_base != base_price:
                warnings.append({
                    "level": "item",
                    "item_index": idx,
                    "name": name,
                    "reason": "unit_price * qty != base_price",
                    "unit_price": unit_price,
                    "qty": qty,
                    "expected_base_price": expected_base,
                    "actual_base_price": base_price,
                    "item": item,
                })

        if qty is None:
            warnings.append({
                "level": "item",
                "item_index": idx,
                "name": name,
                "reason": "qty가 없습니다.",
                "item": item,
            })

        if not name:
            warnings.append({
                "level": "item",
                "item_index": idx,
                "name": name,
                "reason": "item name이 없습니다.",
                "item": item,
            })

        valid_item_count += 1

    return {
        "checked_item_count": checked_item_count,
        "valid_item_count": valid_item_count,
        "invalid_item_count": invalid_item_count,
        "errors": errors,
        "warnings": warnings,
    }


def _validate_receipt_totals(
    items: List[Dict[str, Any]],
    tail_info: Dict[str, Any],
    lines: List[Dict[str, Any]],
) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    summary = tail_info.get("summary", {}) or {}

    # A. item 객체 기반 합계
    computed_base_price_sum = _sum_base_prices(items)
    computed_final_price_sum = _sum_final_prices(items)

    # C. receipt-level 할인 대표값
    # semantic/hanaro_interpreter.py에서 이미
    # 총할인액 우선, 없으면 개별 할인 합산으로 계산되어 들어온 값
    computed_receipt_discount_sum = _safe_int(summary.get("receipt_discount_total")) or 0
    computed_fee_sum = _safe_int(summary.get("fee_total")) or 0

    item_total = _safe_int(summary.get("item_total"))       # 총구매액
    payment_total = _safe_int(summary.get("payment_total")) # 내실금액

    item_total_match: Optional[bool] = None
    payment_total_match: Optional[bool] = None
    qty_match: Optional[bool] = None

    is_total_inferred = False
    inferred_total: Optional[int] = None
    inferred_total_source: Optional[str] = None
    requires_user_total_confirmation = False

    # ---------------------------------------------------------
    # B. 상품 합계 검증
    # Σ item.base_price == 총구매액
    # ---------------------------------------------------------
    if item_total is None:
        warnings.append({
            "level": "receipt",
            "reason": "item_total을 찾지 못했습니다.",
        })
    else:
        item_total_match = (computed_base_price_sum == item_total)

        if not item_total_match:
            errors.append({
                "level": "receipt",
                "reason": "sum(item.base_price) != item_total",
                "computed_base_price_sum": computed_base_price_sum,
                "item_total": item_total,
            })

    # ---------------------------------------------------------
    # D. 최종 결제 검증
    # Σ item.final_price - receipt_discount_total + fee_total == 내실금액
    # ---------------------------------------------------------
    computed_expected_payment_total = (
        computed_final_price_sum
        - computed_receipt_discount_sum
        + computed_fee_sum
    )

    if payment_total is None:
        warnings.append({
            "level": "receipt",
            "reason": "payment_total을 찾지 못했습니다.",
        })

        # 하나로에서 내실금액 라인이 누락된 경우,
        # 총구매액이 아니라 실제 결제 예상 금액으로 복원한다.
        inferred_total = computed_expected_payment_total
        inferred_total_source = "sum(item.final_price) - receipt_discount_total + fee_total"

        payment_total = inferred_total
        is_total_inferred = True
        requires_user_total_confirmation = True
        payment_total_match = None


        warnings.append({
            "level": "receipt",
            "reason": "payment_total이 없어 임시 total을 생성했습니다. 사용자 확인이 필요합니다.",
            "inferred_total": inferred_total,
            "inferred_total_source": inferred_total_source,
        })
    else:
        payment_total_match = (computed_expected_payment_total == payment_total)

        if not payment_total_match:
            errors.append({
                "level": "receipt",
                "reason": "sum(item.final_price) - receipt_discount_total + fee_total != payment_total",
                "computed_final_price_sum": computed_final_price_sum,
                "computed_receipt_discount_sum": computed_receipt_discount_sum,
                "computed_fee_sum": computed_fee_sum,
                "computed_expected_payment_total": computed_expected_payment_total,
                "payment_total": payment_total,
            })

    item_count = len(items)
    item_qty_sum = _sum_item_qty(items)
    receipt_qty = _extract_receipt_qty_from_lines(lines)

    if receipt_qty is not None:
        qty_match = (receipt_qty == item_qty_sum)

        if not qty_match:
            warnings.append({
                "level": "receipt",
                "reason": "receipt_qty != sum(item.qty)",
                "receipt_qty": receipt_qty,
                "item_qty_sum": item_qty_sum,
            })

    receipt_total_source = _extract_receipt_total_source_from_summary(summary)
    if is_total_inferred:
        receipt_total_source = f"inferred:{inferred_total_source}"

    return {
        "computed_base_price_sum": computed_base_price_sum,
        "computed_final_price_sum": computed_final_price_sum,
        "computed_receipt_discount_sum": computed_receipt_discount_sum,
        "computed_fee_sum": computed_fee_sum,
        "computed_expected_payment_total": computed_expected_payment_total,

        "item_total": item_total,
        "payment_total": payment_total,
        "receipt_total": payment_total,
        "receipt_total_source": receipt_total_source,

        "item_total_match": item_total_match,
        "payment_total_match": payment_total_match,
        "total_match": payment_total_match,

        "item_count": item_count,
        "item_qty_sum": item_qty_sum,
        "receipt_qty": receipt_qty,
        "qty_match": qty_match,

        "is_total_inferred": is_total_inferred,
        "inferred_total": inferred_total,
        "inferred_total_source": inferred_total_source,
        "requires_user_total_confirmation": requires_user_total_confirmation,

        "errors": errors,
        "warnings": warnings,
    }


def _sum_base_prices(items: List[Dict[str, Any]]) -> int:
    total = 0
    for item in items:
        base_price = item.get("base_price")
        if isinstance(base_price, int):
            total += base_price
    return total


def _sum_final_prices(items: List[Dict[str, Any]]) -> int:
    total = 0
    for item in items:
        final_price = item.get("final_price")
        if isinstance(final_price, int):
            total += final_price
    return total


def _sum_item_qty(items: List[Dict[str, Any]]) -> int:
    total = 0
    for item in items:
        qty = item.get("qty")
        if isinstance(qty, int):
            total += qty
    return total


def _extract_receipt_qty_from_lines(lines: List[Dict[str, Any]]) -> Optional[int]:
    for row in lines:
        if row.get("line_type") != "receipt_qty":
            continue

        receipt_qty = row.get("receipt_qty")
        if isinstance(receipt_qty, int):
            return receipt_qty

    return None


def _extract_receipt_total_source_from_summary(summary: Dict[str, Any]) -> Optional[str]:
    payment_total = _safe_int(summary.get("payment_total"))
    item_total = _safe_int(summary.get("item_total"))

    if payment_total is not None:
        return "tail_info.summary.payment_total"

    if item_total is not None:
        return "tail_info.summary.item_total"

    return None


def _build_recapture_decision(
    errors: List[Dict[str, Any]],
    warnings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    reasons: List[str] = []

    has_missing_item_core = any(
        err.get("level") == "item"
        and err.get("reason") == "base_price 또는 final_price가 없습니다."
        for err in errors
    )
    if has_missing_item_core:
        reasons.append("item_core_value_missing")

    has_item_total_mismatch = any(
        err.get("level") == "receipt"
        and err.get("reason") == "sum(item.base_price) != item_total"
        for err in errors
    )
    if has_item_total_mismatch:
        reasons.append("item_total_mismatch")

    has_payment_total_mismatch = any(
        err.get("level") == "receipt"
        and err.get("reason") == "sum(item.final_price) - receipt_discount_total + fee_total != payment_total"
        for err in errors
    )
    if has_payment_total_mismatch:
        reasons.append("payment_total_mismatch")

    has_item_price_mismatch = any(
        warn.get("level") == "item"
        and warn.get("reason") == "unit_price * qty != base_price"
        for warn in warnings
    )
    if has_item_price_mismatch:
        reasons.append("item_price_mismatch")

    has_missing_payment_total = any(
        warn.get("level") == "receipt"
        and warn.get("reason") == "payment_total을 찾지 못했습니다."
        for warn in warnings
    )
    if has_missing_payment_total:
        reasons.append("payment_total_missing")

    return {
        "recapture_recommended": len(reasons) >= 2,
        "trigger_count": len(reasons),
        "reasons": reasons,
    }


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None

    try:
        return int(value)
    except Exception:
        return None