from __future__ import annotations

from typing import Any, Dict, List, Optional


def interpret_receipt(parsed_receipt: Dict[str, Any]) -> Dict[str, Any]:
    """
    emart parser output -> semantic interpreted result

    현재 목적:
    - item_name + item_detail 결합
    - discount_detail을 직전 item에 귀속
    - receipt_discount / fee / total / subtotal은 tail_info에 분리 저장
    - 내부 검증용으로 item_total / payment_total / receipt_discount_total / fee_total 계산

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
            "item_total_candidates": [...],
            "payment_total_candidates": [...],
            "summary": {
                "item_total": ...,
                "payment_total": ...,
                "receipt_discount_total": ...,
                "fee_total": ...,
            },
        },
        "lines": parsed lines,
    }
    """
    lines: List[Dict[str, Any]] = parsed_receipt.get("lines", [])
    tail_start_idx = _find_tail_start_index(lines)

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

            # detail 하나 완성되면 pending name 소진
            pending_name = None
            pending_name_line_idx = None
            continue

                # ---------------------------------------------------------
        # 3) discount_detail
        # emart는 직전 완료 item 귀속이 기본
        # - body 구간: item 할인 우선
        # - tail 구간: receipt_discount로 승격 가능
        # ---------------------------------------------------------
        if line_type == "discount_detail":
            text = _clean_text(row.get("line_text")) or ""
            discount_amount = _safe_int(row.get("discount_raw")) or _safe_int(row.get("price_raw"))

            in_tail = (
                tail_start_idx is not None
                and line_idx is not None
                and line_idx >= tail_start_idx
            )

            # -----------------------------------------------------
            # tail 구간 할인 -> receipt_discount
            # -----------------------------------------------------
            if in_tail and discount_amount is not None and discount_amount > 0:
                tail_info["receipt_discounts"].append(
                    {
                        "line_idx": line_idx,
                        "name": _clean_text(row.get("name_raw")) or text,
                        "code": _clean_text(row.get("code")),
                        "discount": discount_amount,
                        "price_raw": _safe_int(row.get("price_raw")),
                        "source_line_indices": [line_idx] if line_idx is not None else [],
                        "kind": "receipt_discount_promoted_from_tail",
                    }
                )
                continue

            # -----------------------------------------------------
            # body 구간 할인 -> item 우선
            # 단독 음수 / 에누리 / 행사 / S-POINT 등
            # -----------------------------------------------------
            if not in_tail:
                if last_completed_item_idx is not None:
                    _attach_discount_to_item(
                        item=items[last_completed_item_idx],
                        row=row,
                        attach_mode="previous_item_fallback",
                    )
                else:
                    tail_info["receipt_discounts"].append(
                        {
                            "line_idx": line_idx,
                            "name": _clean_text(row.get("name_raw")) or text,
                            "discount": discount_amount,
                            "price_raw": _safe_int(row.get("price_raw")),
                            "source_line_indices": [line_idx] if line_idx is not None else [],
                            "kind": "orphan_discount_detail_in_body",
                        }
                    )
                continue

            # -----------------------------------------------------
            # 안전 fallback
            # -----------------------------------------------------
            tail_info["receipt_discounts"].append(
                {
                    "line_idx": line_idx,
                    "name": _clean_text(row.get("name_raw")) or text,
                    "discount": discount_amount,
                    "price_raw": _safe_int(row.get("price_raw")),
                    "source_line_indices": [line_idx] if line_idx is not None else [],
                    "kind": "receipt_discount_fallback",
                }
            )
            continue

        # ---------------------------------------------------------
        # 4) receipt_discount
        # - body 구간이면 직전 item 할인으로 우선 귀속
        # - tail 구간이면 영수증 전역 할인으로 유지
        # ---------------------------------------------------------
        if line_type == "receipt_discount":
            text = _clean_text(row.get("line_text")) or ""
            discount_amount = _safe_int(row.get("discount_raw")) or _safe_int(row.get("price_raw"))

            in_tail = (
                tail_start_idx is not None
                and line_idx is not None
                and line_idx >= tail_start_idx
            )

            # -----------------------------------------------------
            # body 구간의 receipt_discount 후보는 item 할인으로 우선 귀속
            # 예:
            # - 카드할인 -4,000  (합계 전)
            # -----------------------------------------------------
            if not in_tail and last_completed_item_idx is not None:
                _attach_discount_to_item(
                    item=items[last_completed_item_idx],
                    row=row,
                    attach_mode="receipt_discount_reassigned_to_item",
                )
                continue

            # -----------------------------------------------------
            # tail 구간이면 영수증 전역 할인 유지
            # 예:
            # - 삼성카드할인 : 2211101938 -5,000
            # - 결제할인 : -5,000
            # -----------------------------------------------------
            tail_info["receipt_discounts"].append(
                {
                    "line_idx": line_idx,
                    "name": _clean_text(row.get("name_raw")) or text,
                    "code": _clean_text(row.get("code")),
                    "discount": discount_amount,
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
        # - raw totals는 그대로 보존
        # - 내부 검증용으로 item_total / payment_total 후보도 분리
        # ---------------------------------------------------------
        if line_type == "total":
            total_row = {
                "line_idx": line_idx,
                "price": _safe_int(row.get("price_raw")),
                "label": _clean_text(row.get("line_text")),
                "source_line_indices": [line_idx] if line_idx is not None else [],
            }

            tail_info["totals"].append(total_row)

            total_kind = _classify_emart_total_kind(total_row.get("label"))
            total_candidate = {
                **total_row,
                "total_kind": total_kind,
            }

            if total_kind == "payment_total":
                tail_info["payment_total_candidates"].append(total_candidate)
            else:
                tail_info["item_total_candidates"].append(total_candidate)

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

    tail_info["summary"] = _build_tail_summary(items, tail_info)

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
def _find_tail_start_index(lines: List[Dict[str, Any]]) -> Optional[int]:
    """
    emart tail 시작점 탐색

    우선순위:
    1) receipt_qty
    2) total
    3) tax/noise 중 tail 성격 키워드
    """
    for row in lines:
        line_idx = row.get("line_idx")
        line_type = row.get("line_type")
        text = _normalize_text(row.get("line_text"))

        if line_type in {"receipt_qty", "total"}:
            return line_idx

        if any(kw in text for kw in ["면세물품", "과세물품", "부가세", "합계", "결제대상금액"]):
            return line_idx

    return None


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


def _classify_emart_total_kind(label: Any) -> str:
    """
    emart total 라인을 내부 검증용으로 분류
    - 결제대상금액 / 제대상금액 계열 -> payment_total
    - 그 외 합계 계열 -> item_total
    """
    text = _normalize_text(label)

    if "결제대상금액" in text or "제대상금액" in text:
        return "payment_total"

    return "item_total"


def _build_tail_summary(items: List[Dict[str, Any]], tail_info: Dict[str, Any]) -> Dict[str, Optional[int]]:
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
    total = 0

    for row in rows:
        discount = _safe_int(row.get("discount"))
        if discount is not None:
            total += abs(discount)
            continue

        price_raw = _safe_int(row.get("price_raw"))
        if price_raw is not None:
            total += abs(price_raw)

    return total


def _sum_fees(rows: List[Dict[str, Any]]) -> int:
    total = 0

    for row in rows:
        price = _safe_int(row.get("price"))
        if price is not None:
            total += abs(price)

    return total


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return "".join(str(value).strip().split())


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