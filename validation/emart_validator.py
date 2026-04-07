"""
[Validator 역할 정의]

이 모듈은 "이마트 정산 결과 검증"을 담당한다.

검증 종류:

1) item 단위 검증
   - base_price - discount == final_price

2) receipt 단위 검증
   - total 존재 시 → total 기준 검증
   - 없으면 subtotal fallback

3) emart receipt-level discount / fee 반영
   - expected_receipt_total
     = sum(item.final_price) - sum(receipt_discount) + sum(fee)

주의:
- validation은 실패 여부 판단 역할
- 데이터 수정/보정은 하지 않음

출력:
- is_valid
- errors
- warnings
- debug 정보
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def validate_emart(semantic_receipt: Dict[str, Any]) -> Dict[str, Any]:
    items = semantic_receipt.get("items", [])
    tail_info = semantic_receipt.get("tail_info", {})

    item_result = _validate_items(items)
    receipt_result = _validate_receipt_totals(items, tail_info)

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
        "store": "emart",
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
                "computed_final_price_sum": receipt_result["computed_final_price_sum"],
                "receipt_total": receipt_result["payment_total"],
                "receipt_total_source": receipt_result["receipt_total_source"],
                "item_total": receipt_result["item_total"],
                "payment_total": receipt_result["payment_total"],
                "item_total_match": receipt_result["item_total_match"],
                "payment_total_match": receipt_result["payment_total_match"],
                "item_count": receipt_result["item_count"],
                "item_qty_sum": receipt_result["item_qty_sum"],
                "subtotal_count_sum": None,
                "subtotal_count_match": None,
                "computed_receipt_discount_sum": receipt_result["computed_receipt_discount_sum"],
                "computed_fee_sum": receipt_result["computed_fee_sum"],
                "computed_expected_receipt_total": receipt_result["computed_expected_payment_total"],
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
            if unit_price * qty != base_price:
                warnings.append({
                    "level": "item",
                    "item_index": idx,
                    "name": name,
                    "reason": "unit_price * qty != base_price",
                    "unit_price": unit_price,
                    "qty": qty,
                    "expected_base_price": unit_price * qty,
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
) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    computed_final_price_sum = _sum_final_prices(items)

    summary = tail_info.get("summary", {}) or {}

    item_total = _safe_int(summary.get("item_total"))
    payment_total = _safe_int(summary.get("payment_total"))
    computed_receipt_discount_sum = _safe_int(summary.get("receipt_discount_total")) or 0
    computed_fee_sum = _safe_int(summary.get("fee_total")) or 0

    item_total_match: Optional[bool] = None
    payment_total_match: Optional[bool] = None

    is_total_inferred = False
    inferred_total: Optional[int] = None
    inferred_total_source: Optional[str] = None
    requires_user_total_confirmation = False

    if item_total is None:
        warnings.append({
            "level": "receipt",
            "reason": "item_total을 찾지 못했습니다.",
        })
    else:
        item_total_match = (computed_final_price_sum == item_total)

        if not item_total_match:
            errors.append({
                "level": "receipt",
                "reason": "sum(item.final_price) != item_total",
                "computed_final_price_sum": computed_final_price_sum,
                "item_total": item_total,
            })

    computed_expected_payment_total: Optional[int] = None

    if item_total is not None:
        computed_expected_payment_total = (
            item_total
            - computed_receipt_discount_sum
            + computed_fee_sum
        )

    if payment_total is None:
        warnings.append({
            "level": "receipt",
            "reason": "payment_total을 찾지 못했습니다.",
        })

        # ---------------------------------------------------------
        # payment_total이 없으면 임시 total 생성
        # 우선순위:
        # 1) item_total이 있으면 item_total 사용
        # 2) 없으면 sum(item.final_price) 사용
        # ---------------------------------------------------------
        if item_total is not None:
            inferred_total = item_total
            inferred_total_source = "item_total"
        else:
            inferred_total = computed_final_price_sum
            inferred_total_source = "sum(item.final_price)"

        payment_total = inferred_total
        is_total_inferred = True
        requires_user_total_confirmation = True

        warnings.append({
            "level": "receipt",
            "reason": "payment_total이 없어 임시 total을 생성했습니다. 사용자 확인이 필요합니다.",
            "inferred_total": inferred_total,
            "inferred_total_source": inferred_total_source,
        })

    else:
        if computed_expected_payment_total is None:
            warnings.append({
                "level": "receipt",
                "reason": "item_total이 없어 payment_total 계산식을 검증하지 못했습니다.",
            })
        else:
            payment_total_match = (computed_expected_payment_total == payment_total)

            if not payment_total_match:
                errors.append({
                    "level": "receipt",
                    "reason": "item_total - receipt_discount_total + fee_total != payment_total",
                    "item_total": item_total,
                    "computed_receipt_discount_sum": computed_receipt_discount_sum,
                    "computed_fee_sum": computed_fee_sum,
                    "computed_expected_payment_total": computed_expected_payment_total,
                    "payment_total": payment_total,
                })

    item_count = len(items)
    item_qty_sum = _sum_item_qty(items)

    receipt_total_source = _extract_receipt_total_source_from_summary(summary)
    if is_total_inferred:
        receipt_total_source = f"inferred:{inferred_total_source}"

    return {
        "computed_final_price_sum": computed_final_price_sum,
        "computed_receipt_discount_sum": computed_receipt_discount_sum,
        "computed_fee_sum": computed_fee_sum,
        "computed_expected_payment_total": computed_expected_payment_total,
        "item_total": item_total,
        "payment_total": payment_total,
        "receipt_total": payment_total,
        "receipt_total_source": receipt_total_source,
        "total_match": payment_total_match,
        "item_total_match": item_total_match,
        "payment_total_match": payment_total_match,
        "item_count": item_count,
        "item_qty_sum": item_qty_sum,
        "is_total_inferred": is_total_inferred,
        "inferred_total": inferred_total,
        "inferred_total_source": inferred_total_source,
        "requires_user_total_confirmation": requires_user_total_confirmation,
        "errors": errors,
        "warnings": warnings,
    }


def _sum_final_prices(items: List[Dict[str, Any]]) -> int:
    total = 0
    for item in items:
        final_price = item.get("final_price")
        if isinstance(final_price, int):
            total += final_price
    return total


def _sum_receipt_discounts(receipt_discounts: List[Dict[str, Any]]) -> int:
    total = 0

    for row in receipt_discounts:
        amount = _extract_receipt_discount_amount(row)
        if isinstance(amount, int):
            total += amount

    return total


def _sum_fees(fees: List[Dict[str, Any]]) -> int:
    total = 0

    for row in fees:
        amount = _extract_fee_amount(row)
        if isinstance(amount, int):
            total += amount

    return total


def _extract_receipt_discount_amount(row: Dict[str, Any]) -> Optional[int]:
    """
    semantic_interpreter 기준:
    receipt_discounts row 예시
    {
        "discount": ...,
        "price_raw": ...,
        ...
    }

    정책:
    - discount 우선
    - 없으면 price_raw 사용
    - 항상 양수 할인액으로 정규화
    """
    discount = row.get("discount")
    if isinstance(discount, int):
        return abs(discount)

    price_raw = row.get("price_raw")
    if isinstance(price_raw, int):
        return abs(price_raw)

    return None


def _extract_fee_amount(row: Dict[str, Any]) -> Optional[int]:
    """
    semantic_interpreter 기준:
    fees row 예시
    {
        "price": ...,
        ...
    }

    정책:
    - 항상 양수 fee 금액으로 정규화
    """
    price = row.get("price")
    if isinstance(price, int):
        return abs(price)

    return None


def _extract_receipt_total_from_tail_info(tail_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    emart semantic tail_info 구조 기준:
    1) tail_info["totals"]의 마지막 유효 price
    2) tail_info["subtotals"]의 마지막 유효 price
    """
    totals = tail_info.get("totals", [])

    for line in reversed(totals):
        price = line.get("price")
        if isinstance(price, int):
            return {
                "receipt_total": price,
                "receipt_total_source": "totals_last_price",
            }

    subtotals = tail_info.get("subtotals", [])
    for line in reversed(subtotals):
        price = line.get("price")
        if isinstance(price, int):
            return {
                "receipt_total": price,
                "receipt_total_source": "subtotals_last_price",
            }

    return {
        "receipt_total": None,
        "receipt_total_source": None,
    }


def _sum_item_qty(items: List[Dict[str, Any]]) -> int:
    total = 0
    for item in items:
        qty = item.get("qty")
        if isinstance(qty, int):
            total += qty
    return total


def _build_recapture_decision(
    errors: List[Dict[str, Any]],
    warnings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    재촬영 권고 기준:

    아래 신호 중 2개 이상이면 recapture_recommended = True
    1) item 필수값 누락
    2) receipt total mismatch
    3) item 산술 불일치 (unit_price * qty != base_price)
    4) receipt total 미검출
    """
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
        and err.get("reason") == "sum(item.final_price) != item_total"
        for err in errors
    )
    if has_item_total_mismatch:
        reasons.append("item_total_mismatch")

    has_payment_total_mismatch = any(
        err.get("level") == "receipt"
        and err.get("reason") == "item_total - receipt_discount_total + fee_total != payment_total"
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

    trigger_count = len(reasons)

    return {
        "recapture_recommended": trigger_count >= 2,
        "trigger_count": trigger_count,
        "reasons": reasons,
    }


def _extract_receipt_total_source_from_summary(summary: Dict[str, Any]) -> Optional[str]:
    payment_total = _safe_int(summary.get("payment_total"))
    item_total = _safe_int(summary.get("item_total"))

    if payment_total is not None:
        return "tail_info.summary.payment_total"

    if item_total is not None:
        return "tail_info.summary.item_total"

    return None


def _safe_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None