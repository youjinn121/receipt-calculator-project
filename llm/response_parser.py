"""
[Response Parser]

LLM 응답을 허용 카테고리로 정규화하는 모듈.

역할:
- LLM raw 응답에서 카테고리 추출
- 허용 카테고리 외 응답은 Uncategorized 처리
- 따옴표, 마침표, 코드블록, JSON 형태 응답 등 방어
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from llm.category_schema import PRIMARY_CATEGORIES, normalize_category


def parse_category_response(raw_response: Optional[str]) -> str:
    """
    단건 카테고리 응답 파싱.

    기대 응답:
        식재료

    방어 대상:
        "식재료"
        식재료.
        ```식재료```
        {"category": "식재료"}
    """

    if raw_response is None:
        return "Uncategorized"

    text = _clean_response_text(raw_response)

    if not text:
        return "Uncategorized"

    # 1) 정확히 카테고리만 온 경우
    category = normalize_category(text)
    if category != "Uncategorized" or text == "Uncategorized":
        return category

    # 2) JSON 형태 응답 방어
    json_category = _try_extract_category_from_json(text)
    if json_category:
        return normalize_category(json_category)

    # 3) 문장 안에 허용 카테고리가 포함된 경우
    embedded_category = _find_allowed_category_in_text(text)
    if embedded_category:
        return embedded_category

    return "Uncategorized"


def parse_batch_category_response(
    raw_response: Optional[str],
    expected_count: int,
) -> List[str]:
    """
    배치 카테고리 응답 파싱.

    기대 응답:
    [
      {"index": 1, "category": "식재료"},
      {"index": 2, "category": "간식"}
    ]

    실패하거나 개수가 맞지 않으면 부족분은 Uncategorized 처리.
    """

    if expected_count <= 0:
        return []

    results = ["Uncategorized"] * expected_count

    if raw_response is None:
        return results

    text = _clean_response_text(raw_response)

    if not text:
        return results

    parsed = _try_parse_json(text)

    if isinstance(parsed, list):
        for obj in parsed:
            if not isinstance(obj, dict):
                continue

            idx = _safe_int(obj.get("index"))
            category = normalize_category(str(obj.get("category", "")).strip())

            if idx is None:
                continue

            zero_based_idx = idx - 1

            if 0 <= zero_based_idx < expected_count:
                results[zero_based_idx] = category

        return results

    # JSON 실패 시 줄 단위 fallback
    line_categories = _parse_categories_from_lines(text)

    for idx, category in enumerate(line_categories[:expected_count]):
        results[idx] = category

    return results


def _clean_response_text(raw_response: Any) -> str:
    text = str(raw_response or "").strip()

    # markdown code block 제거
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()

    # 흔한 불필요 문자 제거
    text = text.strip()
    text = text.strip('"').strip("'").strip()
    text = text.rstrip(".。").strip()

    return text


def _try_extract_category_from_json(text: str) -> Optional[str]:
    parsed = _try_parse_json(text)

    if isinstance(parsed, dict):
        value = parsed.get("category")
        if value is not None:
            return str(value).strip()

    if isinstance(parsed, list) and parsed:
        first = parsed[0]
        if isinstance(first, dict) and first.get("category") is not None:
            return str(first.get("category")).strip()

    return None


def _try_parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return None


def _find_allowed_category_in_text(text: str) -> Optional[str]:
    compact = re.sub(r"\s+", "", text)

    for category in PRIMARY_CATEGORIES:
        if category == "Uncategorized":
            continue

        if category in text or category in compact:
            return category

    if "Uncategorized" in text:
        return "Uncategorized"

    return None


def _parse_categories_from_lines(text: str) -> List[str]:
    categories: List[str] = []

    for line in text.splitlines():
        cleaned = _clean_response_text(line)

        # 예: 1. 식재료 / 1) 식재료 / - 식재료
        cleaned = re.sub(r"^\s*[-*\d.)]+\s*", "", cleaned).strip()

        category = parse_category_response(cleaned)
        categories.append(category)

    return categories


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None

    try:
        return int(value)
    except Exception:
        return None