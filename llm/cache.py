"""
[Category Cache]

LLM 카테고리 분류 결과 캐시 모듈.

역할:
- 같은 store + item_name 조합은 LLM을 다시 호출하지 않도록 캐싱
- 허용 카테고리만 저장
- 프롬프트/카테고리 스키마가 바뀌면 CACHE_VERSION을 올려 기존 캐시와 분리
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from llm.category_schema import is_allowed_category, normalize_category


CACHE_VERSION = "v1"
DEFAULT_CACHE_PATH = Path("data/llm/category_cache.json")


def load_category_cache(cache_path: str | Path = DEFAULT_CACHE_PATH) -> Dict[str, Dict[str, Any]]:
    path = Path(cache_path)

    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            return data

        return {}

    except Exception:
        return {}


def save_category_cache(
    cache: Dict[str, Dict[str, Any]],
    cache_path: str | Path = DEFAULT_CACHE_PATH,
) -> None:
    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def make_category_cache_key(
    store: str,
    item_name: str,
    *,
    cache_version: str = CACHE_VERSION,
) -> str:
    normalized_store = _normalize_key_text(store)
    normalized_name = _normalize_item_name(item_name)

    return f"{cache_version}:{normalized_store}:{normalized_name}"


def get_cached_category(
    cache: Dict[str, Dict[str, Any]],
    store: str,
    item_name: str,
) -> Optional[Dict[str, Any]]:
    key = make_category_cache_key(store, item_name)
    row = cache.get(key)

    if not isinstance(row, dict):
        return None

    category = normalize_category(row.get("category", ""))

    if not is_allowed_category(category):
        return None

    return {
        "category": category,
        "category_meta": {
            "method": "cache",
            "cache_hit": True,
            "cache_key": key,
            "cached_from_method": row.get("method", "llm"),
            "raw_response": row.get("raw_response"),
            "use_fallback": False,
            "use_llm": False,
        },
    }


def set_cached_category(
    cache: Dict[str, Dict[str, Any]],
    store: str,
    item_name: str,
    category: str,
    *,
    raw_response: Optional[str] = None,
    method: str = "llm",
) -> None:
    normalized_category = normalize_category(category)

    if not is_allowed_category(normalized_category):
        normalized_category = "Uncategorized"

    key = make_category_cache_key(store, item_name)

    cache[key] = {
        "store": _normalize_key_text(store),
        "item_name": str(item_name or "").strip(),
        "normalized_item_name": _normalize_item_name(item_name),
        "category": normalized_category,
        "method": method,
        "raw_response": raw_response,
        "cache_version": CACHE_VERSION,
    }


def clear_category_cache(cache_path: str | Path = DEFAULT_CACHE_PATH) -> None:
    path = Path(cache_path)

    if path.exists():
        path.unlink()


def _normalize_key_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", "", text)
    return text


def _normalize_item_name(value: Any) -> str:
    text = str(value or "").strip().lower()

    # 상품명 비교용 정규화
    # 예: "동물복지란 30구" == "동물복지란30구"
    text = re.sub(r"\s+", "", text)

    # 영수증 상품명에서 자주 섞이는 구분자 제거
    text = re.sub(r"[\"'`]", "", text)

    return text