"""
[Category Normalizer]

semantic item 객체에 LLM 기반 카테고리를 부여하는 모듈.

흐름:
1. 캐시 조회
2. 캐시 hit → LLM 호출 없이 category 부여
3. 캐시 miss → prompt 생성
4. LLM 호출
5. response_parser로 응답 정규화
6. 캐시에 저장
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Dict, Iterable, List, Optional

from llm.cache import (
    get_cached_category,
    load_category_cache,
    save_category_cache,
    set_cached_category,
)
from llm.category_schema import PRIMARY_CATEGORIES, normalize_category
from llm.prompt_builder import build_category_prompt
from llm.response_parser import parse_category_response


LLMCaller = Callable[[str], str]


def normalize_item_category(
    item: Dict[str, Any],
    store: str,
    basket_items: Optional[Iterable[str]],
    llm_caller: LLMCaller,
    *,
    use_cache: bool = True,
    save_cache: bool = True,
    cache_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    단일 item에 category/category_meta를 붙여 반환한다.
    원본 item은 수정하지 않는다.
    """

    normalized_item = deepcopy(item)
    item_name = _safe_str(normalized_item.get("name"))

    if not item_name:
        normalized_item["category"] = "Uncategorized"
        normalized_item["category_meta"] = {
            "method": "fallback",
            "reason": "empty_item_name",
            "raw_response": None,
            "allowed_categories": PRIMARY_CATEGORIES,
            "use_fallback": True,
            "use_llm": False,
            "cache_hit": False,
        }
        return normalized_item

    cache = load_category_cache(cache_path) if cache_path else load_category_cache()

    if use_cache:
        cached = get_cached_category(cache, store, item_name)
        if cached:
            normalized_item["category"] = cached["category"]
            normalized_item["category_meta"] = {
                **cached["category_meta"],
                "allowed_categories": PRIMARY_CATEGORIES,
            }
            return normalized_item

    prompt = build_category_prompt(
        item=normalized_item,
        store=store,
        basket_items=basket_items,
    )

    try:
        raw_response = llm_caller(prompt)
        category = parse_category_response(raw_response)
        category = normalize_category(category)

        normalized_item["category"] = category
        normalized_item["category_meta"] = {
            "method": "llm",
            "raw_response": raw_response,
            "allowed_categories": PRIMARY_CATEGORIES,
            "use_fallback": category == "Uncategorized",
            "use_llm": True,
            "cache_hit": False,
        }

        if save_cache:
            set_cached_category(
                cache=cache,
                store=store,
                item_name=item_name,
                category=category,
                raw_response=raw_response,
                method="llm",
            )

            if cache_path:
                save_category_cache(cache, cache_path)
            else:
                save_category_cache(cache)

        return normalized_item

    except Exception as e:
        normalized_item["category"] = "Uncategorized"
        normalized_item["category_meta"] = {
            "method": "fallback",
            "reason": "llm_call_failed",
            "error": str(e),
            "raw_response": None,
            "allowed_categories": PRIMARY_CATEGORIES,
            "use_fallback": True,
            "use_llm": True,
            "cache_hit": False,
        }

        return normalized_item


def normalize_receipt_categories(
    semantic_receipt: Dict[str, Any],
    llm_caller: LLMCaller,
    *,
    use_cache: bool = True,
    save_cache: bool = True,
    cache_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    영수증 semantic 결과 전체에 category를 붙여 반환한다.
    원본 semantic_receipt는 수정하지 않는다.
    """

    result = deepcopy(semantic_receipt)

    store = _safe_str(result.get("store"))
    items = result.get("items", [])

    if not isinstance(items, list):
        result["items"] = []
        return result

    basket_items = [
        _safe_str(item.get("name"))
        for item in items
        if isinstance(item, dict) and _safe_str(item.get("name"))
    ]

    categorized_items: List[Dict[str, Any]] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        categorized_item = normalize_item_category(
            item=item,
            store=store,
            basket_items=basket_items,
            llm_caller=llm_caller,
            use_cache=use_cache,
            save_cache=save_cache,
            cache_path=cache_path,
        )

        categorized_items.append(categorized_item)

    result["items"] = categorized_items

    return result


def _safe_str(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()