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
from llm.cache import (
    get_cached_category,
    load_category_cache,
    save_category_cache,
    set_cached_category,
)

def categorize_receipt_items(
    semantic_receipt: Dict[str, Any],
    model: Optional[str] = None,
    use_llm: bool = True,
    use_fallback: bool = False,
    use_cache: bool = True,
    save_cache: bool = True,
    cache_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    semantic receipt의 items에 category 필드를 추가한다.

    처리 우선순위:
    1. fallback 사용 시 fallback rule
    2. cache 사용 시 cached category
    3. LLM 호출
    4. 실패/비허용 응답은 Uncategorized
    """

    result = dict(semantic_receipt)
    items = [dict(item) for item in semantic_receipt.get("items", [])]

    store = str(semantic_receipt.get("store") or "").lower()
    basket_names = [
        str(item.get("name", "")).strip()
        for item in items
        if str(item.get("name", "")).strip()
    ]

    cache = load_category_cache(cache_path) if cache_path else load_category_cache()

    categorized_items: List[Dict[str, Any]] = []
    cache_updated = False

    for item in items:
        item_name = str(item.get("name") or "").strip()

        category = "Uncategorized"
        raw_response = None
        method = "disabled"
        cache_hit = False

        # 1) fallback rule
        if use_fallback:
            fallback_category = apply_fallback_category(item)

            if fallback_category is not None:
                category = fallback_category
                method = "fallback"

        # 2) cache lookup
        if category == "Uncategorized" and use_cache and item_name:
            cached = get_cached_category(
                cache=cache,
                store=store,
                item_name=item_name,
            )

            if cached:
                category = cached["category"]
                method = "cache"
                raw_response = cached.get("category_meta", {}).get("raw_response")
                cache_hit = True

        # 3) LLM call
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

            if save_cache and item_name:
                set_cached_category(
                    cache=cache,
                    store=store,
                    item_name=item_name,
                    category=category,
                    raw_response=raw_response,
                    method="llm",
                )
                cache_updated = True

        item["category"] = category
        item["category_meta"] = {
            "method": method,
            "raw_response": raw_response,
            "allowed_categories": PRIMARY_CATEGORIES,
            "use_fallback": use_fallback,
            "use_llm": use_llm,
            "use_cache": use_cache,
            "cache_hit": cache_hit,
        }

        categorized_items.append(item)

    if cache_updated:
        if cache_path:
            save_category_cache(cache, cache_path)
        else:
            save_category_cache(cache)

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
    use_cache: bool = True,
    save_cache: bool = True,
    cache_path: Optional[str] = None,
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
        use_cache=use_cache,
        save_cache=save_cache,
        cache_path=cache_path,
)

    return result.get("items", [])


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None

    try:
        return int(value)
    except Exception:
        return None