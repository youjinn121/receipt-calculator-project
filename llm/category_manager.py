"""
[Category Manager]

Semantic 결과에 LLM 카테고리 정규화를 적용하는 모듈.

흐름:
semantic_receipt
→ item별 prompt 생성
→ LLM 호출
→ 응답 파싱
→ item["category"] 추가
→ category_summary 생성

주의:
- validation 통과 데이터에 적용하는 것을 권장
- LLM 실패 또는 허용 외 응답은 Uncategorized 처리
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from llm.category_schema import PRIMARY_CATEGORIES
from llm.prompt_builder import build_category_prompt
from llm.llm_client import call_llm
from llm.response_parser import parse_category_response
from llm.fallback_rules import apply_fallback_category
from llm.metrics import attach_category_metrics

def categorize_receipt_items(
    semantic_receipt: Dict[str, Any],
    model: Optional[str] = None,
    use_llm: bool = True,
    use_fallback: bool = False,
) -> Dict[str, Any]:
    """
    semantic receipt의 items에 category 필드를 추가한다.
    """

    result = dict(semantic_receipt)
    items = [dict(item) for item in semantic_receipt.get("items", [])]

    store = str(semantic_receipt.get("store") or "").lower()
    basket_names = [
        str(item.get("name", "")).strip()
        for item in items
        if str(item.get("name", "")).strip()
    ]

    categorized_items: List[Dict[str, Any]] = []

    for item in items:
        category = "Uncategorized"
        raw_response = None
        method = "disabled"

        if use_fallback:
            fallback_category = apply_fallback_category(item)

            if fallback_category is not None:
                category = fallback_category
                method = "fallback"

        if category == "Uncategorized" and use_llm:
            prompt = build_category_prompt(
                item=item,
                store=store,
                basket_items=basket_names,
            )

            if model:
                raw_response = call_llm(prompt=prompt, model=model)
            else:
                raw_response = call_llm(prompt=prompt)

            category = parse_category_response(raw_response)
            method = "llm"

        item["category"] = category
        item["category_meta"] = {
            "method": method,
            "raw_response": raw_response,
            "allowed_categories": PRIMARY_CATEGORIES,
            "use_fallback": use_fallback,
            "use_llm": use_llm,
        }

        categorized_items.append(item)

    result["items"] = categorized_items
    result["category_summary"] = build_category_summary(categorized_items)

    result = attach_category_metrics(result)

    return result


def build_category_summary(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    카테고리별 금액/개수 집계.
    """

    summary: Dict[str, Dict[str, int]] = {}

    for category in PRIMARY_CATEGORIES:
        summary[category] = {
            "item_count": 0,
            "qty_sum": 0,
            "final_price_sum": 0,
        }

    for item in items:
        category = str(item.get("category") or "Uncategorized").strip()

        if category not in summary:
            category = "Uncategorized"

        qty = _safe_int(item.get("qty")) or 0
        final_price = _safe_int(item.get("final_price")) or 0

        summary[category]["item_count"] += 1
        summary[category]["qty_sum"] += qty
        summary[category]["final_price_sum"] += final_price

    return summary


def categorize_items_only(
    items: List[Dict[str, Any]],
    store: str,
    model: Optional[str] = None,
    use_llm: bool = True,
    use_fallback: bool = False,
) -> List[Dict[str, Any]]:
    """
    receipt 전체가 아니라 items 리스트만 분류할 때 사용.
    """

    semantic_receipt = {
        "store": store,
        "items": items,
    }

    result = categorize_receipt_items(
        semantic_receipt=semantic_receipt,
        model=model,
        use_llm=use_llm,
        use_fallback=use_fallback,
    )

    return result.get("items", [])


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None

    try:
        return int(value)
    except Exception:
        return None