from __future__ import annotations

from typing import Any, Dict, List, Optional


def interpret_receipt(parsed_receipt: Dict[str, Any]) -> Dict[str, Any]:
    """
    hanaro parser output -> semantic interpreted result

    역할:
    - item_name + item_detail 결합
    - discount_detail을 직전 item에 귀속
    - receipt_discount / subtotal / total을 tail_info에 분리 저장
    - item_total / payment_total / receipt_discount_total 계산
    """

    lines: List[Dict[str, Any]] = parsed_receipt.get("lines", [])

    items: List[Dict[str, Any]] = []
    tail_info: Dict[str, Any] = {
        "totals": [],
        "subtotals": [],
        "receipt_discounts": [],
        "fees": [],
        "item_total_candidates": [],
        "payment_total_candidates": [],
        "summary": {
            "item_total": None,
            "payment_total": None,
            "receipt_discount_total": 0,
            "fee_total": 0,
        },
    }

    pending_name: Optional[str] = None
    pending_name_line_idx: Optional[int] = None
    last_completed_item_idx: Optional[int] = None

    for row in lines:
        line_type = row.get("line_type")
        line_idx = row.get("line_idx")

        # ---------------------------------------------------------
        # 1) item_name
        # ---------------------------------------------------------
        if line_type == "item_name":
            name_raw = _clean_text(row.get("name_raw")) or _clean_text(row.get("line_text"))

            if name_raw:
                pending_name = name_raw
                pending_name_line_idx = line_idx

            continue

        # ---------------------------------------------------------
        # 2) item_detail
        # ---------------------------------------------------------
        if line_type == "item_detail":
            item = _build_item_from_detail_row(
                row=row,
                pending_name=pending_name,
                pending_name_line_idx=pending_name_line_idx,
            )

            items.append(item)
            last_completed_item_idx = len(items) - 1

            pending_name = None
            pending_name_line_idx = None
            continue

        # ---------------------------------------------------------
        # 3) discount_detail
        # 하나로 item-level 할인은 직전 완료 item에 귀속
        # 예:
        # - 삼겹 한돈자조금 할인 -1.369
        # - c9900015039990 -5,000 1 -5.000
        # ---------------------------------------------------------
        if line_type == "discount_detail":
            discount_amount = _safe_int(row.get("discount_raw")) or _safe_int(row.get("price_raw"))

            if last_completed_item_idx is not None and discount_amount is not None and discount_amount > 0:
                _attach_discount_to_item(
                    item=items[last_completed_item_idx],
                    row=row,
                    attach_mode="previous_item_fallback",
                )
            else:
                tail_info["receipt_discounts"].append(
                    {
                        "line_idx": line_idx,
                        "name": _clean_text(row.get("name_raw")) or _clean_text(row.get("line_text")),
                        "code": _clean_text(row.get("code")),
                        "discount": discount_amount,
                        "price_raw": _safe_int(row.get("price_raw")),
                        "source_line_indices": [line_idx] if line_idx is not None else [],
                        "kind": "orphan_discount_detail",
                    }
                )

            continue

        # ---------------------------------------------------------
        # 4) receipt_discount
        # 하나로 receipt-level 할인은 item에 귀속하지 않고 tail_info에 보관
        # 예:
        # - 끝전할인: -4
        # - 쿠폰할인: -660
        # - 총할인액: -4
        # - 농축산물 할인쿠폰 (4월2차) -1,400
        # ---------------------------------------------------------
        if line_type == "receipt_discount":
            discount_amount = _safe_int(row.get("discount_raw")) or _safe_int(row.get("price_raw"))

            tail_info["receipt_discounts"].append(
                {
                    "line_idx": line_idx,
                    "name": _clean_text(row.get("name_raw")) or _clean_text(row.get("line_text")),
                    "code": _clean_text(row.get("code")),
                    "discount": discount_amount,
                    "price_raw": _safe_int(row.get("price_raw")),
                    "source_line_indices": [line_idx] if line_idx is not None else [],
                    "kind": "receipt_discount",
                }
            )
            continue

        # ---------------------------------------------------------
        # 5) subtotal
        # 하나로 총구매액
        # ---------------------------------------------------------
        if line_type == "subtotal":
            subtotal_row = {
                "line_idx": line_idx,
                "price": _safe_int(row.get("price_raw")),
                "subtotal_count": _safe_int(row.get("subtotal_count")),
                "label": _clean_text(row.get("line_text")),
                "source_line_indices": [line_idx] if line_idx is not None else [],
            }

            tail_info["subtotals"].append(subtotal_row)

            item_total_candidate = {
                **subtotal_row,
                "total_kind": "item_total",
            }
            tail_info["item_total_candidates"].append(item_total_candidate)
            continue

        # ---------------------------------------------------------
        # 6) total
        # 하나로 내실금액
        # ---------------------------------------------------------
        if line_type == "total":
            total_row = {
                "line_idx": line_idx,
                "price": _safe_int(row.get("price_raw")),
                "label": _clean_text(row.get("line_text")),
                "source_line_indices": [line_idx] if line_idx is not None else [],
            }

            tail_info["totals"].append(total_row)

            payment_total_candidate = {
                **total_row,
                "total_kind": "payment_total",
            }
            tail_info["payment_total_candidates"].append(payment_total_candidate)
            continue

        # ---------------------------------------------------------
        # 7) fee
        # 현재 하나로에서는 거의 없지만 공통 schema 유지
        # ---------------------------------------------------------
        if line_type == "fee":
            tail_info["fees"].append(
                {
                    "line_idx": line_idx,
                    "name": _clean_text(row.get("name_raw")),
                    "price": _safe_int(row.get("price_raw")),
                    "qty": _safe_int(row.get("qty")),
                    "source_line_indices": [line_idx] if line_idx is not None else [],
                    "kind": "fee",
                }
            )
            continue

        # noise / discount_keyword / 기타는 semantic에서 소비하지 않음
        continue

    tail_info["summary"] = _build_tail_summary(tail_info)

    return {
        "file_name": parsed_receipt.get("file_name", ""),
        "file_meta": parsed_receipt.get("file_meta", {}),
        "store": "hanaro",
        "items": items,
        "tail_info": tail_info,
        "lines": lines,
    }


# =========================================================
# Internal helpers
# =========================================================

def _build_item_from_detail_row(
    row: Dict[str, Any],
    pending_name: Optional[str],
    pending_name_line_idx: Optional[int],
) -> Dict[str, Any]:
    line_idx = row.get("line_idx")

    code = _clean_text(row.get("code"))
    qty = _safe_int(row.get("qty")) or 1
    unit_price = _safe_int(row.get("unit_price_raw"))
    price_raw = _safe_int(row.get("price_raw"))
    detail_name = _clean_text(row.get("name_raw"))

    if pending_name:
        name = pending_name
        name_source = "item_name+item_detail"
        source_line_indices = [
            idx for idx in [pending_name_line_idx, line_idx]
            if idx is not None
        ]
    elif detail_name:
        name = detail_name
        name_source = "item_detail_inline_name"
        source_line_indices = [line_idx] if line_idx is not None else []
    elif code:
        name = code
        name_source = "item_detail_code_fallback"
        source_line_indices = [line_idx] if line_idx is not None else []
    else:
        name = "UNKNOWN_ITEM"
        name_source = "unknown"
        source_line_indices = [line_idx] if line_idx is not None else []

    if price_raw is not None:
        base_price = price_raw
    elif unit_price is not None and qty is not None:
        base_price = unit_price * qty
    else:
        base_price = None

    discount = 0
    final_price = base_price

    return {
        "name": name,
        "name_source": name_source,
        "code": code,
        "qty": qty,
        "unit_price": unit_price,
        "base_price": base_price,
        "discount": discount,
        "final_price": final_price,
        "discount_meta": [],
        "source_line_indices": source_line_indices,
    }


def _attach_discount_to_item(
    item: Dict[str, Any],
    row: Dict[str, Any],
    attach_mode: str,
) -> None:
    line_idx = row.get("line_idx")
    discount_amount = _safe_int(row.get("discount_raw")) or _safe_int(row.get("price_raw")) or 0
    discount_name = _clean_text(row.get("name_raw")) or _clean_text(row.get("line_text"))

    item["discount"] = (_safe_int(item.get("discount")) or 0) + abs(discount_amount)

    base_price = _safe_int(item.get("base_price"))
    if base_price is not None:
        item["final_price"] = max(base_price - item["discount"], 0)

    source_line_indices = item.get("source_line_indices", [])
    if line_idx is not None and line_idx not in source_line_indices:
        source_line_indices.append(line_idx)
        item["source_line_indices"] = source_line_indices

    discount_meta = item.get("discount_meta", [])
    discount_meta.append(
        {
            "line_idx": line_idx,
            "discount_name": discount_name,
            "discount_amount": abs(discount_amount),
            "discount_code": _clean_text(row.get("code")),
            "attach_mode": attach_mode,
            "source_line_indices": [line_idx] if line_idx is not None else [],
        }
    )
    item["discount_meta"] = discount_meta


def _build_tail_summary(tail_info: Dict[str, Any]) -> Dict[str, Optional[int]]:
    item_total = _extract_last_price(tail_info.get("item_total_candidates", []))
    payment_total = _extract_last_price(tail_info.get("payment_total_candidates", []))
    receipt_discount_total = _sum_receipt_discounts(tail_info.get("receipt_discounts", []))
    fee_total = _sum_fees(tail_info.get("fees", []))

    return {
        "item_total": item_total,
        "payment_total": payment_total,
        "receipt_discount_total": receipt_discount_total,
        "fee_total": fee_total,
    }


def _extract_last_price(rows: List[Dict[str, Any]]) -> Optional[int]:
    for row in reversed(rows):
        price = _safe_int(row.get("price"))
        if price is not None:
            return price
    return None


def _sum_receipt_discounts(rows: List[Dict[str, Any]]) -> int:
    """
    하나로 receipt-level 할인 합산 정책

    1. 총할인액이 있으면 최종 할인 대표값으로 사용
    2. 총할인액이 없으면 개별 할인 라인 합산
       예: 끝전할인, 쿠폰할인, 이벤트할인 등
    """
    summary_discount_total: Optional[int] = None
    detail_discount_total = 0

    for row in rows:
        name = _clean_text(row.get("name")) or ""

        discount = _safe_int(row.get("discount"))
        if discount is None:
            discount = _safe_int(row.get("price_raw"))

        if discount is None:
            continue

        discount = abs(discount)

        if "총할인액" in name:
            summary_discount_total = discount
        else:
            detail_discount_total += discount

    if summary_discount_total is not None:
        return summary_discount_total

    return detail_discount_total


def _sum_fees(rows: List[Dict[str, Any]]) -> int:
    total = 0

    for row in rows:
        price = _safe_int(row.get("price"))
        if price is not None:
            total += abs(price)

    return total


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None

    try:
        return int(value)
    except Exception:
        return None


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    return " ".join(text.split())