from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional

from receipt_parser.normalizer import (
    cast_amount_token,
    cast_discount_amount,
    cast_qty_token,
    cleanup_name_candidate,
)


def extract_fields(
    line_text: str,
    normalized_line_text: str,
    line_type: str,
    store: str,
    store_rules: Any,
) -> Dict[str, Any]:
    """
    line_type이 정해진 뒤, 필요한 필드만 추출한다.

    반환 필드:
    - code
    - qty
    - unit_price_raw
    - price_raw
    - discount_raw
    - name_raw
    - subtotal_count
    """
    base = _empty_fields()

    raw = (line_text or "").strip()
    text = (normalized_line_text or "").strip()

    if not text:
        return base

    if line_type == "item_detail":
        parsed = _parse_detail_line(
            text=text,
            patterns=store_rules.get("item_patterns", []),
            is_discount=False,
        )
        base.update(parsed)
        return base

    if line_type == "discount_detail":
        parsed = _parse_detail_line(
            text=text,
            patterns=store_rules.get("discount_patterns", []),
            is_discount=True,
        )
        base.update(parsed)
        return base

    if line_type == "subtotal":
        subtotal_count = _extract_subtotal_count(text)
        last_amount = _extract_last_amount(text)

        base["subtotal_count"] = subtotal_count

        # count-only subtotal 예:
        # "상품수 소계 : 10"
        # -> 이 경우 price_raw까지 10으로 넣지 않음
        if last_amount is not None and last_amount != subtotal_count:
            base["price_raw"] = last_amount

        return base

    if line_type == "total":
        base["price_raw"] = _extract_last_amount(text)
        return base

    if line_type in {"item_name", "discount_target"}:
        base["name_raw"] = cleanup_name_candidate(
            text=raw,
            store=store,
            store_rules=store_rules,
        )
        return base

    if line_type == "discount_keyword":
        # CPN 같은 키워드 라인은 필드 추출 없음
        return base

    if line_type == "noise":
        return base

    return base


# =========================================================
# Internal helpers
# =========================================================

def _empty_fields() -> Dict[str, Any]:
    return {
        "code": None,
        "qty": None,
        "unit_price_raw": None,
        "price_raw": None,
        "discount_raw": None,
        "name_raw": None,
        "subtotal_count": None,
    }


def _parse_detail_line(
    text: str,
    patterns: Iterable[re.Pattern],
    is_discount: bool,
) -> Dict[str, Any]:
    """
    item_detail / discount_detail 패턴 매칭 후 필드 추출
    """
    for pattern in patterns:
        m = pattern.match(text)
        if not m:
            continue

        gd = m.groupdict()

        code = gd.get("code")
        qty = cast_qty_token(gd.get("qty"))
        unit_price_raw = cast_amount_token(gd.get("unit_price"))
        price_raw = cast_amount_token(gd.get("price"))

        # qty 누락 케이스 보정
        # ex) 630218 7990 7,990 T
        if qty is None:
            qty = _infer_qty_as_one_when_missing(
                unit_price_raw=unit_price_raw,
                price_raw=price_raw,
            )

        result = {
            "code": code,
            "qty": qty,
            "unit_price_raw": abs(unit_price_raw) if isinstance(unit_price_raw, int) else None,
            "price_raw": abs(price_raw) if isinstance(price_raw, int) else None,
            "discount_raw": None,
            "name_raw": None,
            "subtotal_count": None,
        }

        if is_discount:
            result["discount_raw"] = cast_discount_amount(gd.get("price"))
            if result["discount_raw"] is None and result["price_raw"] is not None:
                result["discount_raw"] = result["price_raw"]

        return result

    return _empty_fields()


def _infer_qty_as_one_when_missing(
    unit_price_raw: Optional[int],
    price_raw: Optional[int],
) -> Optional[int]:
    """
    최소 규칙:
    qty 그룹이 없는데 unit_price == price 이면 qty=1로 본다.
    """
    if unit_price_raw is None or price_raw is None:
        return None

    if abs(unit_price_raw) == abs(price_raw):
        return 1

    return None


def _extract_subtotal_count(text: str) -> Optional[int]:
    """
    subtotal 라인에서 상품 개수 추출

    예:
    - 상품수 소계 : 10
    - (Sub-총상품수 : 13) 144420
    - (Sub-총상품 : 5)
    - (Sub-총싱품수 : 6) 80510

    규칙:
    1) subtotal 관련 키워드 뒤의 첫 숫자를 우선 count로 본다.
    2) 마지막 금액(price_raw)과 혼동하지 않도록 '마지막 숫자'가 아니라
       키워드 근처 숫자를 잡는다.
    """
    if not text:
        return None

    compact = re.sub(r"\s+", "", text)

    patterns = [
        r"(?:상품수소계|총상품수|총싱품수|총상품)\D*(\d+)",
        r"(?:Sub[-_]?(?:총상품수|총싱품수|총상품))\D*(\d+)",
    ]

    for pattern in patterns:
        m = re.search(pattern, compact, flags=re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except (TypeError, ValueError):
                return None

    return None


def _extract_last_amount(text: str) -> Optional[int]:
    """
    subtotal / total 라인에서 마지막 금액 추출

    예:
    - 상품수 소계 : 10
    - 합계 (VAT 포함) 232,330
    - (Sub-총상품수 : 13) 144420
    """
    candidates = re.findall(r"[+-]?\d[\d,]*-?[Tt]?", text)
    if not candidates:
        return None

    return cast_amount_token(candidates[-1])