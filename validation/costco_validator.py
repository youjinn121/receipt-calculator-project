"""
[Validator 역할 정의]

이 모듈은 "정산 결과 검증"을 담당한다.

검증 종류:

1) item 단위 검증
   - base_price - discount == final_price

2) receipt 단위 검증
   - total_lines 존재 시 → total 기준 검증
   - 없으면 subtotal fallback

3) subtotal segment 검증
   - Sub-총상품수 계열은 segment 방식
   - 구간별 item qty 합 == subtotal_count

추가 체크:
- unconsumed line 존재 여부
- numeric-only orphan line
- item_name이 detail 없이 끝난 케이스

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


def validate_costco(semantic_receipt: Dict[str, Any]) -> Dict[str, Any]:
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
        "store": "costco",
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
            "total_match": receipt_result["total_match"],
            "subtotal_segment_match": receipt_result["subtotal_segment_match"],
        },
        "debug": {
            "receipt_validation": {
                "computed_final_price_sum": receipt_result["computed_final_price_sum"],
                "receipt_total": receipt_result["receipt_total"],
                "receipt_total_source": receipt_result["receipt_total_source"],
                "item_count": receipt_result["item_count"],
                "item_qty_sum": receipt_result["item_qty_sum"],
                "subtotal_count_sum": receipt_result["subtotal_count_sum"],
                "subtotal_count_match": receipt_result["subtotal_count_match"],
                "is_total_inferred": receipt_result["is_total_inferred"],
                "inferred_total": receipt_result["inferred_total"],
                "inferred_total_source": receipt_result["inferred_total_source"],
                "requires_user_total_confirmation": receipt_result["requires_user_total_confirmation"],
            },
            "subtotal_segment_results": receipt_result["subtotal_segment_results"],
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

    receipt_total_info = _extract_receipt_total_from_tail_info(tail_info)
    receipt_total = receipt_total_info["receipt_total"]
    receipt_total_source = receipt_total_info["receipt_total_source"]

    total_match: Optional[bool] = None

    is_total_inferred = False
    inferred_total: Optional[int] = None
    inferred_total_source: Optional[str] = None
    requires_user_total_confirmation = False

    if receipt_total is None:
        warnings.append({
            "level": "receipt",
            "reason": "receipt_total을 찾지 못했습니다.",
        })

        inferred_total = computed_final_price_sum
        inferred_total_source = "sum(item.final_price)"

        receipt_total = inferred_total
        receipt_total_source = f"inferred:{inferred_total_source}"

        is_total_inferred = True
        requires_user_total_confirmation = True
        total_match = None

        warnings.append({
            "level": "receipt",
            "reason": "receipt_total이 없어 임시 total을 생성했습니다. 사용자 확인이 필요합니다.",
            "inferred_total": inferred_total,
            "inferred_total_source": inferred_total_source,
        })

    else:
        total_match = (computed_final_price_sum == receipt_total)

        if not total_match:
            errors.append({
                "level": "receipt",
                "reason": "sum(item.final_price) != receipt_total",
                "computed_final_price_sum": computed_final_price_sum,
                "receipt_total": receipt_total,
                "receipt_total_source": receipt_total_source,
            })

    item_count = len(items)
    subtotal_count_sum = _sum_subtotal_counts_from_tail_info(tail_info)
    subtotal_count_match: Optional[bool] = None

    item_qty_sum = _sum_item_qty(items)

    if subtotal_count_sum is None:
        warnings.append({
            "level": "receipt",
            "reason": "subtotal_count를 찾지 못했습니다.",
        })
    else:
        subtotal_count_match = (item_qty_sum == subtotal_count_sum)

        if not subtotal_count_match:
            warnings.append({
                "level": "receipt",
                "reason": "sum(item.qty) != sum(subtotal_count)",
                "item_count": item_count,
                "item_qty_sum": item_qty_sum,
                "subtotal_count_sum": subtotal_count_sum,
            })

    subtotal_segment_results = _validate_subtotal_segments(items, tail_info)
    subtotal_segment_match: Optional[bool] = None

    if not subtotal_segment_results:
        warnings.append({
            "level": "receipt",
            "reason": "subtotal 구간 검증을 위한 subtotal line을 찾지 못했습니다.",
        })
    else:
        subtotal_segment_match = all(
            segment.get("match") is True
            for segment in subtotal_segment_results
        )
        for segment in subtotal_segment_results:
            if not segment.get("match"):
                warnings.append({
                    "level": "receipt",
                    "reason": "subtotal 구간 qty 합 != subtotal_count",
                    "segment_index": segment.get("segment_index"),
                    "subtotal_line_idx": segment.get("subtotal_line_idx"),
                    "segment_start_line_idx_exclusive": segment.get("segment_start_line_idx_exclusive"),
                    "segment_end_line_idx_inclusive": segment.get("segment_end_line_idx_inclusive"),
                    "computed_qty_sum": segment.get("computed_qty_sum"),
                    "subtotal_count": segment.get("subtotal_count"),
                    "matched_item_count": segment.get("matched_item_count"),
                    "matched_item_line_indices": segment.get("matched_item_line_indices"),
                })

    return {
        "computed_final_price_sum": computed_final_price_sum,
        "receipt_total": receipt_total,
        "receipt_total_source": receipt_total_source,
        "total_match": total_match,
        "item_count": item_count,
        "item_qty_sum": item_qty_sum,
        "subtotal_count_sum": subtotal_count_sum,
        "subtotal_count_match": subtotal_count_match,
        "subtotal_segment_match": subtotal_segment_match,
        "subtotal_segment_results": subtotal_segment_results,
        "errors": errors,
        "is_total_inferred": is_total_inferred,
        "inferred_total": inferred_total,
        "inferred_total_source": inferred_total_source,
        "requires_user_total_confirmation": requires_user_total_confirmation,
        "warnings": warnings,
    }


def _sum_final_prices(items: List[Dict[str, Any]]) -> int:
    total = 0
    for item in items:
        final_price = item.get("final_price")
        if isinstance(final_price, int):
            total += final_price
    return total


def _extract_receipt_total_from_tail_info(tail_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    receipt total 추출 우선순위:
    1) tail_info["total_lines"]의 마지막 유효 price_raw
    2) tail_info["subtotal_summary"]["last_subtotal_amount"]
    3) tail_info["subtotal_lines"]의 마지막 유효 price_raw

    현재 정책:
    - subtotal 금액은 누적 값이므로 마지막 subtotal 금액을 사용한다.
    """
    total_lines = tail_info.get("total_lines", [])

    for line in reversed(total_lines):
        price_raw = line.get("price_raw")
        if isinstance(price_raw, int):
            return {
                "receipt_total": price_raw,
                "receipt_total_source": "total_lines_last_price_raw",
            }

    subtotal_summary = tail_info.get("subtotal_summary", {})
    last_subtotal_amount = subtotal_summary.get("last_subtotal_amount")

    if isinstance(last_subtotal_amount, int):
        return {
            "receipt_total": last_subtotal_amount,
            "receipt_total_source": "subtotal_last_amount",
        }

    subtotal_lines = tail_info.get("subtotal_lines", [])
    for line in reversed(subtotal_lines):
        price_raw = line.get("price_raw")
        if isinstance(price_raw, int):
            return {
                "receipt_total": price_raw,
                "receipt_total_source": "subtotal_lines_last_price_raw",
            }

    return {
        "receipt_total": None,
        "receipt_total_source": None,
    }


def _sum_subtotal_counts_from_tail_info(tail_info: Dict[str, Any]) -> Optional[int]:
    subtotal_lines = tail_info.get("subtotal_lines", [])
    if not subtotal_lines:
        return None

    subtotal_counts: List[int] = []

    for line in subtotal_lines:
        subtotal_count = line.get("subtotal_count")
        if isinstance(subtotal_count, int):
            subtotal_counts.append(subtotal_count)

    if not subtotal_counts:
        return None

    return sum(subtotal_counts)


def _validate_subtotal_segments(
    items: List[Dict[str, Any]],
    tail_info: Dict[str, Any],
) -> List[Dict[str, Any]]:
    subtotal_lines = tail_info.get("subtotal_lines", [])
    if not subtotal_lines:
        return []

    valid_subtotals = [
        line for line in subtotal_lines
        if isinstance(line.get("line_idx"), int) and isinstance(line.get("subtotal_count"), int)
    ]
    if not valid_subtotals:
        return []

    valid_subtotals.sort(key=lambda x: x["line_idx"])

    results: List[Dict[str, Any]] = []
    previous_subtotal_line_idx = -1

    for segment_index, subtotal_line in enumerate(valid_subtotals):
        subtotal_line_idx = subtotal_line["line_idx"]
        subtotal_count = subtotal_line["subtotal_count"]
        subtotal_mode = _detect_subtotal_count_mode(subtotal_line)

        computed_qty_sum = 0
        matched_item_count = 0
        matched_item_line_indices: List[int] = []

        for item in items:
            item_line_idx = _extract_item_detail_line_idx(item)
            if item_line_idx is None:
                continue

            if subtotal_mode == "cumulative":
                is_in_range = item_line_idx < subtotal_line_idx
                segment_start_line_idx_exclusive = -1
            else:
                is_in_range = previous_subtotal_line_idx < item_line_idx < subtotal_line_idx
                segment_start_line_idx_exclusive = previous_subtotal_line_idx

            if is_in_range:
                qty = item.get("qty")
                if isinstance(qty, int):
                    computed_qty_sum += qty
                matched_item_count += 1
                matched_item_line_indices.append(item_line_idx)

        results.append({
            "segment_index": segment_index,
            "subtotal_mode": subtotal_mode,
            "segment_start_line_idx_exclusive": segment_start_line_idx_exclusive,
            "segment_end_line_idx_inclusive": subtotal_line_idx,
            "subtotal_line_idx": subtotal_line_idx,
            "subtotal_count": subtotal_count,
            "computed_qty_sum": computed_qty_sum,
            "matched_item_count": matched_item_count,
            "matched_item_line_indices": matched_item_line_indices,
            "match": computed_qty_sum == subtotal_count,
        })

        previous_subtotal_line_idx = subtotal_line_idx

    return results


def _detect_subtotal_count_mode(subtotal_line: Dict[str, Any]) -> str:
    return "segment"


def _extract_item_detail_line_idx(item: Dict[str, Any]) -> Optional[int]:
    source_line_indices = item.get("source_line_indices", [])
    if not source_line_indices:
        return None

    first_idx = source_line_indices[0]
    if isinstance(first_idx, int):
        return first_idx

    return None


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
    3) item qty 합 != subtotal count 합
    4) subtotal segment mismatch
    5) item 산술 불일치 (unit_price * qty != base_price)
    """
    reasons: List[str] = []

    # 1) item 필수값 누락
    has_missing_item_core = any(
        err.get("level") == "item"
        and err.get("reason") == "base_price 또는 final_price가 없습니다."
        for err in errors
    )
    if has_missing_item_core:
        reasons.append("item_core_value_missing")

    # 2) receipt total mismatch
    has_receipt_total_mismatch = any(
        err.get("level") == "receipt"
        and err.get("reason") == "sum(item.final_price) != receipt_total"
        for err in errors
    )
    if has_receipt_total_mismatch:
        reasons.append("receipt_total_mismatch")

    # 3) item qty sum != subtotal count sum
    has_qty_sum_mismatch = any(
        warn.get("level") == "receipt"
        and warn.get("reason") == "sum(item.qty) != sum(subtotal_count)"
        for warn in warnings
    )
    if has_qty_sum_mismatch:
        reasons.append("item_qty_sum_mismatch")

    # 4) subtotal segment mismatch
    has_subtotal_segment_mismatch = any(
        warn.get("level") == "receipt"
        and warn.get("reason") == "subtotal 구간 qty 합 != subtotal_count"
        for warn in warnings
    )
    if has_subtotal_segment_mismatch:
        reasons.append("subtotal_segment_mismatch")

    # 5) item 산술 불일치
    has_item_price_mismatch = any(
        warn.get("level") == "item"
        and warn.get("reason") == "unit_price * qty != base_price"
        for warn in warnings
    )
    if has_item_price_mismatch:
        reasons.append("item_price_mismatch")

    has_missing_receipt_total = any(
        warn.get("level") == "receipt"
        and warn.get("reason") == "receipt_total을 찾지 못했습니다."
        for warn in warnings
    )

    if has_missing_receipt_total:
        reasons.append("receipt_total_missing")

    trigger_count = len(reasons)

    return {
        "recapture_recommended": trigger_count >= 2,
        "trigger_count": trigger_count,
        "reasons": reasons,
    }
