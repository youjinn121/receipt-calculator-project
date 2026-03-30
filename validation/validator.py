from __future__ import annotations

from typing import Any, Dict, List, Optional


def validate_receipt(semantic_receipt: Dict[str, Any]) -> Dict[str, Any]:
    """
    semantic 결과를 검증한다.

    입력:
    {
      "file_name": "...",
      "store": "...",
      "items": [...],
      "tail_info": {...}
    }

    출력:
    {
      "file_name": "...",
      "store": "...",
      "is_valid": True/False,
      "item_validation": {...},
      "receipt_validation": {...},
      "errors": [...],
      "warnings": [...],
    }
    """
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

    return {
        "file_name": semantic_receipt.get("file_name", ""),
        "file_meta": semantic_receipt.get("file_meta", {}),
        "store": semantic_receipt.get("store", ""),
        "is_valid": len(errors) == 0,
        "item_validation": {
            "checked_item_count": item_result["checked_item_count"],
            "valid_item_count": item_result["valid_item_count"],
            "invalid_item_count": item_result["invalid_item_count"],
        },
        "receipt_validation": {
            "computed_final_price_sum": receipt_result["computed_final_price_sum"],
            "receipt_total": receipt_result["receipt_total"],
            "total_match": receipt_result["total_match"],
            "item_count": receipt_result["item_count"],
            "subtotal_count_sum": receipt_result["subtotal_count_sum"],
            "subtotal_count_match": receipt_result["subtotal_count_match"],
            "subtotal_segment_match": receipt_result["subtotal_segment_match"],
            "subtotal_segment_results": receipt_result["subtotal_segment_results"],
        },
        "errors": errors,
        "warnings": warnings,
    }


# =========================================================
# Item-level validation
# =========================================================

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

        # =========================================================
        # 1️⃣ 필수값 체크
        # =========================================================
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

        # =========================================================
        # 2️⃣ 할인 계산 검증
        # =========================================================
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

        # =========================================================
        # 3️⃣ unit_price × qty 검증
        # =========================================================
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

        # =========================================================
        # 4️⃣ 기타 경고
        # =========================================================

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


# =========================================================
# Receipt-level validation
# =========================================================

def _validate_receipt_totals(
    items: List[Dict[str, Any]],
    tail_info: Dict[str, Any],
) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    computed_final_price_sum = _sum_final_prices(items)
    receipt_total = _extract_receipt_total_from_tail_info(tail_info)

    total_match: Optional[bool] = None

    if receipt_total is None:
        warnings.append({
            "level": "receipt",
            "reason": "receipt total을 찾지 못했습니다.",
        })
    else:
        total_match = (computed_final_price_sum == receipt_total)

        if not total_match:
            errors.append({
                "level": "receipt",
                "reason": "sum(item.final_price) != receipt_total",
                "computed_final_price_sum": computed_final_price_sum,
                "receipt_total": receipt_total,
            })

    item_count = len(items)
    subtotal_count_sum = _sum_subtotal_counts_from_tail_info(tail_info)
    subtotal_count_match: Optional[bool] = None

    if subtotal_count_sum is None:
        warnings.append({
            "level": "receipt",
            "reason": "subtotal_count를 찾지 못했습니다.",
        })
    else:
        subtotal_count_match = (item_count == subtotal_count_sum)

        if not subtotal_count_match:
            warnings.append({
                "level": "receipt",
                "reason": "len(items) != sum(subtotal_count)",
                "item_count": item_count,
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
        "total_match": total_match,
        "item_count": item_count,
        "subtotal_count_sum": subtotal_count_sum,
        "subtotal_count_match": subtotal_count_match,
        "subtotal_segment_match": subtotal_segment_match,
        "subtotal_segment_results": subtotal_segment_results,
        "errors": errors,
        "warnings": warnings,
    }


# =========================================================
# Utility
# =========================================================

def _sum_final_prices(items: List[Dict[str, Any]]) -> int:
    total = 0
    for item in items:
        final_price = item.get("final_price")
        if isinstance(final_price, int):
            total += final_price
    return total


def _extract_receipt_total_from_tail_info(tail_info: Dict[str, Any]) -> Optional[int]:
    """
    tail_info["total_lines"]에서 receipt total 추출
    현재 parser 구조 기준:
    total line의 price_raw 사용
    """
    total_lines = tail_info.get("total_lines", [])
    if not total_lines:
        return None

    # 마지막 total line 우선 사용
    for line in reversed(total_lines):
        price_raw = line.get("price_raw")
        if isinstance(price_raw, int):
            return price_raw

    return None


def _sum_subtotal_counts_from_tail_info(tail_info: Dict[str, Any]) -> Optional[int]:
    """
    tail_info["subtotal_lines"]에서 subtotal_count를 모두 합산한다.

    예:
    - 상품수 소계 : 10
    - (Sub-총상품수 : 13) 144420

    subtotal_count가 하나도 없으면 None 반환
    """
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
    """
    subtotal 구간 검증

    규칙:
    - 상품수 소계: 직전 subtotal 다음부터 현재 subtotal 전까지의 item qty 합과 비교
    - Sub-총상품수 / Sub-총싱품수 / Sub-총상품: receipt 시작부터 현재 subtotal 전까지의 누적 item qty 합과 비교
    - 할인 detail qty는 제외해야 하므로 semantic item의 qty만 사용한다.
    - semantic item의 source_line_indices 첫 번째 값은 item_detail line_idx라고 가정한다.
    """
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
    """
    subtotal 라인의 count 해석 모드 판별

    반환:
    - "segment": 상품수 소계
    - "cumulative": Sub-총상품수 / Sub-총싱품수 / Sub-총상품
    """
    text = (
        subtotal_line.get("normalized_line_text")
        or subtotal_line.get("line_text")
        or ""
    )
    compact = str(text).replace(" ", "").lower()

    if "sub-총상품수" in compact or "sub-총싱품수" in compact or "sub-총상품" in compact:
        return "cumulative"

    return "segment"


def _extract_item_detail_line_idx(item: Dict[str, Any]) -> Optional[int]:
    """
    semantic item에서 item_detail line_idx 추출

    현재 구조:
    - item 생성 시 source_line_indices = [item_detail_line_idx]
    - 이후 discount가 붙으면 source_line_indices에 discount_detail line_idx가 append 됨

    따라서 첫 번째 source_line_indices를 item_detail line_idx로 사용한다.
    """
    source_line_indices = item.get("source_line_indices", [])
    if not source_line_indices:
        return None

    first_idx = source_line_indices[0]
    if isinstance(first_idx, int):
        return first_idx

    return None