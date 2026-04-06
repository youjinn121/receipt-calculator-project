from __future__ import annotations

from typing import Any, Dict, List, Optional


def interpret_receipt(parsed_receipt: Dict[str, Any]) -> Dict[str, Any]:
    """
    emart parser output -> semantic interpreted result

    현재 목적:
    - item_name + item_detail 결합
    - discount_detail을 직전 item에 귀속
    - receipt_discount / fee / total / subtotal은 tail_info에 분리 저장

    반환 구조:
    {
        "file_name": ...,
        "file_meta": ...,
        "store": "emart",
        "items": [...],
        "tail_info": {
            "totals": [...],
            "subtotals": [...],
            "receipt_discounts": [...],
            "fees": [...],
        },
        "lines": parsed lines,
    }
    """
    lines: List[Dict[str, Any]] = parsed_receipt.get("lines", [])

    items: List[Dict[str, Any]] = []
    tail_info: Dict[str, List[Dict[str, Any]]] = {
        "totals": [],
        "subtotals": [],
        "receipt_discounts": [],
        "fees": [],
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

            # detail 하나 완성되면 pending name 소진
            pending_name = None
            pending_name_line_idx = None
            continue

        # ---------------------------------------------------------
        # 3) discount_detail
        # emart는 직전 완료 item 귀속이 기본
        # ---------------------------------------------------------
        if line_type == "discount_detail":
            if last_completed_item_idx is not None:
                _attach_discount_to_item(
                    item=items[last_completed_item_idx],
                    row=row,
                    attach_mode="previous_item_fallback",
                )
            else:
                # 귀속할 item이 없으면 tail 쪽에 보조로 남김
                tail_info["receipt_discounts"].append(
                    {
                        "line_idx": line_idx,
                        "name": _clean_text(row.get("name_raw")),
                        "discount": _safe_int(row.get("discount_raw")),
                        "source_line_indices": [line_idx] if line_idx is not None else [],
                        "kind": "orphan_discount_detail",
                    }
                )
            continue

        # ---------------------------------------------------------
        # 4) receipt_discount
        # ---------------------------------------------------------
        if line_type == "receipt_discount":
            tail_info["receipt_discounts"].append(
                {
                    "line_idx": line_idx,
                    "name": _clean_text(row.get("name_raw")),
                    "code": _clean_text(row.get("code")),
                    "discount": _safe_int(row.get("discount_raw")),
                    "price_raw": _safe_int(row.get("price_raw")),
                    "source_line_indices": [line_idx] if line_idx is not None else [],
                    "kind": "receipt_discount",
                }
            )
            continue

        # ---------------------------------------------------------
        # 5) fee
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

        # ---------------------------------------------------------
        # 6) total
        # ---------------------------------------------------------
        if line_type == "total":
            tail_info["totals"].append(
                {
                    "line_idx": line_idx,
                    "price": _safe_int(row.get("price_raw")),
                    "label": _clean_text(row.get("line_text")),
                    "source_line_indices": [line_idx] if line_idx is not None else [],
                }
            )
            continue

        # ---------------------------------------------------------
        # 7) subtotal
        # ---------------------------------------------------------
        if line_type == "subtotal":
            tail_info["subtotals"].append(
                {
                    "line_idx": line_idx,
                    "price": _safe_int(row.get("price_raw")),
                    "subtotal_count": _safe_int(row.get("subtotal_count")),
                    "label": _clean_text(row.get("line_text")),
                    "source_line_indices": [line_idx] if line_idx is not None else [],
                }
            )
            continue

        # ---------------------------------------------------------
        # 8) noise / discount_keyword / discount_target 등
        # emart 현재 구조에서는 대부분 무시
        # ---------------------------------------------------------
        continue

    return {
        "file_name": parsed_receipt.get("file_name", ""),
        "file_meta": parsed_receipt.get("file_meta", {}),
        "store": "emart",
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
    """
    item_detail row 하나로 item 생성
    """
    line_idx = row.get("line_idx")
    code = _clean_text(row.get("code"))
    qty = _safe_int(row.get("qty")) or 1
    unit_price = _safe_int(row.get("unit_price_raw"))
    price_raw = _safe_int(row.get("price_raw"))
    detail_name = _clean_text(row.get("name_raw"))

    # 이름 결정 우선순위
    if pending_name:
        name = pending_name
        name_source = "item_name+item_detail"
        source_line_indices = [idx for idx in [pending_name_line_idx, line_idx] if idx is not None]
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

    # base_price
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
    """
    discount_detail을 item에 귀속
    """
    line_idx = row.get("line_idx")
    discount_amount = _safe_int(row.get("discount_raw")) or 0
    discount_name = _clean_text(row.get("name_raw"))

    item["discount"] = (_safe_int(item.get("discount")) or 0) + discount_amount

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
            "discount_amount": discount_amount,
            "attach_mode": attach_mode,
            "source_line_indices": [line_idx] if line_idx is not None else [],
        }
    )
    item["discount_meta"] = discount_meta


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