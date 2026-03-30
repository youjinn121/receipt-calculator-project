from __future__ import annotations

from typing import Any, Dict


SUPPORTED_STORES = {"costco", "emart", "hanaro"}


def normalize_store_name(store: str) -> str:
    """
    store 문자열 정규화
    """
    if store is None:
        raise ValueError("store 값이 None 입니다.")

    normalized = str(store).strip().lower()

    if not normalized:
        raise ValueError("store 값이 비어 있습니다.")

    return normalized


def get_store_rules(store: str) -> Any:
    """
    store 이름에 맞는 rules 객체 반환

    lazy import 방식 → 필요한 store만 import
    """
    normalized_store = normalize_store_name(store)

    if normalized_store == "costco":
        from receipt_parser.store_rules.costco_rules import COSTCO_RULES
        return COSTCO_RULES

    if normalized_store == "emart":
        from receipt_parser.store_rules.emart_rules import EMART_RULES
        return EMART_RULES

    if normalized_store == "hanaro":
        from receipt_parser.store_rules.hanaro_rules import HANARO_RULES
        return HANARO_RULES

    raise ValueError(
        f"지원하지 않는 store 입니다: {store!r}. "
        f"지원 목록: {sorted(SUPPORTED_STORES)}"
    )