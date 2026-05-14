"""
[Category Manager]

Semantic 결과에 LLM 카테고리 정규화를 적용하는 모듈.

흐름:
semantic_receipt
→ item별 prompt 생성
→ LLM 호출
→ 응답 파싱
→ 기타/Uncategorized 응답에 한정한 보수적 fallback
→ item["category"] 추가
→ category_summary 생성

주의:
- validation 통과 데이터에 적용하는 것을 권장
- LLM 실패 또는 허용 외 응답은 Uncategorized 처리
"""

from __future__ import annotations

import re
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


# LLM이 기타/Uncategorized로 보수 응답했을 때만 적용하는 마지막 의미 토큰 기반 복구 규칙.
# 정상 카테고리를 이미 낸 경우에는 절대 덮어쓰지 않는다.
LAST_TOKEN_CATEGORY_RULES = {
    "식재료": {
        "바나나",
        "과일",
        "채소",
        "버섯",
        "맛타리",
        "시즈닝",
        "후추",
        "식초",
        "드레싱",
        "소스",
        "피클",
        "치즈",
        "생크림",
        "스테비아",
    },
    "간식": {
        "베이글",
        "페스츄리",
        "크라상",
        "무스",
        "쿠키",
        "비스킷",
        "초콜릿",
        "약과",
    },
    "음료": {
        "우유",
        "밀크",
        "커피",
        "드립백",
        "비피더스",
        "엔요",
        "요구르트",
        "콤부차",
    },
    "생활용품": {
        "샴푸",
        "세제",
        "비닐백",
        "봉투",
        "화장지",
        "키친타월",
        "물티슈",
    },
}


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
    4. LLM 결과가 기타/Uncategorized일 때만 마지막 의미 토큰 기반 복구
    5. 실패/비허용 응답은 Uncategorized
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
        last_token_fallback = False
        category_before_last_token_fallback = None
        last_token = None

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

        # 4) LLM/cache/fallback 결과가 기타 또는 Uncategorized일 때만 보수적 복구
        category_before_last_token_fallback = category
        recovered_category, last_token = recover_category_by_last_token(
            name=item_name,
            current_category=category,
        )

        if recovered_category != category:
            category = recovered_category
            last_token_fallback = True

        # cache는 최종 category 기준으로 저장한다.
        # 단, cache hit로 가져온 경우에는 다시 저장하지 않는다.
        if (
            method == "llm"
            and save_cache
            and item_name
            and not cache_hit
        ):
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
            "last_token_fallback": last_token_fallback,
            "category_before_last_token_fallback": category_before_last_token_fallback,
            "last_token": last_token,
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


def recover_category_by_last_token(name: str, current_category: str) -> tuple[str, Optional[str]]:
    """
    LLM이 기타/Uncategorized로 분류한 경우에만 적용하는 보수적 fallback.

    목적:
    - 브랜드명 + 상품군명 구조에서 앞 단어 때문에 기타로 빠지는 케이스 복구
      예) 델몬트 바나나 -> 바나나 기준 식재료
    - 복합 상품명에서 앞 단어와 뒤 단어가 충돌할 때, 마지막 의미 토큰을 우선
      예) 스테이크 시즈닝 -> 시즈닝 기준 식재료

    주의:
    - 정상 카테고리를 LLM이 이미 낸 경우에는 절대 덮어쓰지 않는다.
    - 기타로 가기 직전 복구용이다.
    """

    if current_category not in {"기타", "Uncategorized"}:
        return current_category, None

    last_token = _extract_last_meaningful_token(name)

    if not last_token:
        return current_category, None

    for category, keywords in LAST_TOKEN_CATEGORY_RULES.items():
        for keyword in keywords:
            if keyword in last_token:
                return category, last_token

    return current_category, last_token


def _extract_last_meaningful_token(name: str) -> str:
    if not name:
        return ""

    text = str(name).strip()

    if not text:
        return ""

    # 용량/수량/단위 제거
    # 예) 바나나 1.5KG -> 바나나
    # 예) 치즈 180g -> 치즈
    text = re.sub(
        r"\b\d+(?:\.\d+)?\s*(?:g|kg|ml|l|G|KG|ML|L|입|개|EA|ea)\b",
        " ",
        text,
    )

    # 단독 숫자 제거
    text = re.sub(r"\b\d+(?:\.\d+)?\b", " ", text)

    # 괄호/기호는 토큰 분리자로 처리
    text = re.sub(r"[\[\]\(\)\{\}/,&+*_:\-]", " ", text)

    # 중복 공백 제거
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return ""

    tokens = [token.strip() for token in text.split(" ") if token.strip()]

    if not tokens:
        return ""

    return tokens[-1]


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