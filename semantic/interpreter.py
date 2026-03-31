from __future__ import annotations

from typing import Any, Dict, List, Optional


def interpret_receipt(parsed_receipt: Dict[str, Any]) -> Dict[str, Any]:
    """
    parser 결과(receipt 단위)를 받아 semantic item 결과를 만든다.

    입력:
    {
      "file_name": "...",
      "store": "costco",
      "lines": [...]
    }

    출력:
    {
      "file_name": "...",
      "store": "costco",
      "items": [...],
      "tail_info": {...}
    }
    """
    lines = parsed_receipt.get("lines", [])
    items: List[Dict[str, Any]] = []

    pending_item_name: Optional[str] = None
    pending_discount_keyword: Optional[str] = None
    pending_discount_target: Optional[str] = None

    # discount_detail fallback용: 가장 최근 completed item 기억
    last_completed_item: Optional[Dict[str, Any]] = None

    tail_info = {
        "subtotal_lines": [],
        "subtotal_summary": {
            "count_candidates": [],
            "amount_candidates": [],
            "last_subtotal_count": None,
            "last_subtotal_amount": None,
            "max_subtotal_count": None,
            "max_subtotal_amount": None,
        },
        "total_lines": [],
        "noise_lines": [],
    }

    for line in lines:
        line_type = line.get("line_type")

        if line_type == "item_name":
            current_name = (
                line.get("name_raw")
                or line.get("normalized_line_text")
                or line.get("line_text")
            )

            # =========================================================
            # 1) discount_keyword 다음 줄 item_name → discount_target
            # ex)
            #   CPN
            #   정통어묵탕모듬
            #   641491 1x 2,600 2,600-T
            # =========================================================
            if pending_discount_keyword and not pending_discount_target:
                pending_discount_target = current_name
                continue

            # 일반 item_name 후보
            pending_item_name = current_name
            continue

        if line_type == "item_detail":
            item = _build_item_from_detail_line(
                line=line,
                pending_item_name=pending_item_name,
            )
            items.append(item)

            # 최근 completed item 기억
            last_completed_item = item

            # item이 만들어졌으면 name pending 해제
            pending_item_name = None
            continue

        if line_type == "discount_keyword":
            pending_discount_keyword = (
                line.get("normalized_line_text")
                or line.get("line_text")
            )
            continue

        if line_type == "discount_target":
            pending_discount_target = (
                line.get("name_raw")
                or line.get("normalized_line_text")
                or line.get("line_text")
            )
            continue

        if line_type == "discount_detail":
            # =========================================================
            # 2) discount_keyword도 없고 explicit target도 없으면
            #    discount_detail 직전 completed item을 fallback target으로 사용
            # =========================================================
            if not pending_discount_target and last_completed_item is not None:
                fallback_target_name = last_completed_item.get("name")
                if fallback_target_name:
                    pending_discount_target = fallback_target_name

            _attach_discount_to_item(
                items=items,
                discount_line=line,
                pending_discount_keyword=pending_discount_keyword,
                pending_discount_target=pending_discount_target,
            )

            # 할인 블록 처리 후 pending 해제
            pending_discount_keyword = None
            pending_discount_target = None
            continue

        if line_type == "subtotal":
            tail_info["subtotal_lines"].append(line)
            _update_subtotal_summary(tail_info["subtotal_summary"], line)
            continue

        if line_type == "total":
            tail_info["total_lines"].append(line)
            continue

        if line_type == "noise":
            tail_info["noise_lines"].append(line)
            continue

    _finalize_items(items)

    return {
        "file_name": parsed_receipt.get("file_name", ""),
        "file_meta": parsed_receipt.get("file_meta", {}),
        "store": parsed_receipt.get("store", ""),
        "items": items,
        "tail_info": tail_info,
    }


# =========================================================
# Internal helpers
# =========================================================

def _build_item_from_detail_line(
    line: Dict[str, Any],
    pending_item_name: Optional[str],
) -> Dict[str, Any]:
    """
    item_detail line으로 item 생성
    """
    unit_price_raw = line.get("unit_price_raw")
    qty = line.get("qty")
    price_raw = line.get("price_raw")

    item = {
        "name": pending_item_name,
        "name_source": "item_name+item_detail" if pending_item_name else "item_detail_only",
        "code": line.get("code"),
        "qty": qty,
        "unit_price": unit_price_raw,
        "base_price": price_raw,
        "discount": 0,
        "final_price": price_raw,
        "discount_meta": [],
        "source_line_indices": [line.get("line_idx")],
    }

    return item


def _attach_discount_to_item(
    items: List[Dict[str, Any]],
    discount_line: Dict[str, Any],
    pending_discount_keyword: Optional[str],
    pending_discount_target: Optional[str],
) -> None:
    """
    discount_detail을 item에 귀속

    우선순위:
    1. discount_target이 있으면 뒤에서부터 이름 매칭
    2. 없으면 직전 item에 부착
    """
    if not items:
        return

    discount_amount = discount_line.get("discount_raw") or 0
    if not discount_amount:
        return

    target_item = None

    # 1) discount_target 기준 매칭
    if pending_discount_target:
        target_item = _find_target_item_by_name(items, pending_discount_target)

    # 2) 못 찾으면 직전 item
    if target_item is None:
        target_item = items[-1]

    target_item["discount"] = (target_item.get("discount") or 0) + discount_amount
    target_item["final_price"] = (target_item.get("base_price") or 0) - (target_item.get("discount") or 0)

    target_item["discount_meta"].append({
        "discount_keyword": pending_discount_keyword,
        "discount_target": pending_discount_target,
        "discount_code": discount_line.get("code"),
        "discount_amount": discount_amount,
        "source_line_idx": discount_line.get("line_idx"),
    })

    target_item["source_line_indices"].append(discount_line.get("line_idx"))


def _find_target_item_by_name(
    items: List[Dict[str, Any]],
    discount_target_name: str,
) -> Optional[Dict[str, Any]]:
    """
    뒤에서부터 가장 가까운 item name 매칭
    Costco 최소 규칙용
    """
    target_norm = _normalize_name_for_match(discount_target_name)

    if not target_norm:
        return None

    for item in reversed(items):
        item_name = item.get("name")
        item_norm = _normalize_name_for_match(item_name)

        if not item_norm:
            continue

        if target_norm in item_norm or item_norm in target_norm:
            return item

    return None


def _normalize_name_for_match(name: Optional[str]) -> str:
    """
    semantic 매칭용 간단 정규화
    - 공백 제거
    - IRC/EXM/PP suffix 제거
    """
    if not name:
        return ""

    text = str(name).strip()

    # suffix 제거
    for suffix in (" IRC", " EXM", " PP", "IRC", "EXM", "PP"):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()

    # 공백 제거
    text = text.replace(" ", "")
    return text


def _update_subtotal_summary(
    subtotal_summary: Dict[str, Any],
    subtotal_line: Dict[str, Any],
) -> None:
    """
    subtotal line을 요약 정보에 반영한다.

    보관 목적:
    - 나중에 receipt 검증 시 subtotal count / subtotal amount 후보 활용
    - tail section 종료 판단 보조 정보 활용
    """
    subtotal_count = subtotal_line.get("subtotal_count")
    subtotal_amount = subtotal_line.get("price_raw")

    if isinstance(subtotal_count, int):
        subtotal_summary["count_candidates"].append(subtotal_count)
        subtotal_summary["last_subtotal_count"] = subtotal_count

        current_max_count = subtotal_summary.get("max_subtotal_count")
        if current_max_count is None or subtotal_count > current_max_count:
            subtotal_summary["max_subtotal_count"] = subtotal_count

    if isinstance(subtotal_amount, int):
        subtotal_summary["amount_candidates"].append(subtotal_amount)
        subtotal_summary["last_subtotal_amount"] = subtotal_amount

        current_max_amount = subtotal_summary.get("max_subtotal_amount")
        if current_max_amount is None or subtotal_amount > current_max_amount:
            subtotal_summary["max_subtotal_amount"] = subtotal_amount


def _finalize_items(items: List[Dict[str, Any]]) -> None:
    """
    item 최종 보정
    """
    for item in items:
        base_price = item.get("base_price") or 0
        discount = item.get("discount") or 0

        item["final_price"] = base_price - discount