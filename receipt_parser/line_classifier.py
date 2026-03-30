from __future__ import annotations

import re
from typing import Any, Iterable


def classify_line(
    line_text: str,
    normalized_line_text: str,
    store: str,
    store_rules: Any,
) -> str:
    raw = _normalize_space(line_text)
    text = _normalize_space(normalized_line_text)

    if not text:
        return "noise"

    # =========================================================
    # 1) noise
    # =========================================================
    if _is_noise_line(raw, text, store_rules):
        return "noise"

    # =========================================================
    # 2) subtotal
    # =========================================================
    if _contains_any_keyword(text, store_rules.get("subtotal_keywords", [])):
        return "subtotal"

    # =========================================================
    # 3) total
    # =========================================================
    if _contains_any_keyword(text, store_rules.get("total_keywords", [])):
        return "total"

    # =========================================================
    # 4) tax → noise
    # =========================================================
    if _contains_any_keyword(text, store_rules.get("tax_keywords", [])):
        return "noise"

    # =========================================================
    # 5) discount keyword (CPN 등)
    # =========================================================
    if _is_discount_keyword_line(text, store_rules):
        return "discount_keyword"

    # =========================================================
    # 6) discount detail (휴리스틱 + 패턴)
    # =========================================================
    if _is_discount_detail_line(text):
        return "discount_detail"

    if _matches_any_pattern(text, store_rules.get("discount_patterns", [])):
        return "discount_detail"

    # =========================================================
    # 7) item detail (휴리스틱 + 패턴)
    # =========================================================
    if _is_item_detail_line(text):
        return "item_detail"

    if _matches_any_pattern(text, store_rules.get("item_patterns", [])):
        return "item_detail"

    # =========================================================
    # 8) discount target
    # =========================================================
    if _is_discount_target_line(text, store_rules):
        return "discount_target"

    # =========================================================
    # 9) fallback
    # =========================================================
    return "item_name"


# =========================================================
# Internal helpers
# =========================================================

def _is_noise_line(raw: str, text: str, store_rules: Any) -> bool:
    if _contains_any_keyword(text, store_rules.get("noise_keywords", [])):
        return True

    if re.match(r"^\*[A-Z]+", text):
        return True

    if text in {".", "-", "--", "*", "**", "***", ":"}:
        return True

    return False


# =========================================================
# 🔥 핵심 추가 1: item_detail 휴리스틱
# =========================================================
def _is_item_detail_line(text: str) -> bool:
    """
    조건:
    - 숫자 6~7자리 코드
    - 가격 2개 이상
    """
    tokens = text.split()

    if len(tokens) < 3:
        return False

    # 코드 (6~7자리 숫자)
    if not re.match(r"^\d{4,7}$", tokens[0]):
        return False

    # 가격 개수
    price_tokens = [t for t in tokens if re.match(r"^[\d,]+$", t)]
    if len(price_tokens) >= 2:
        return True

    return False


# =========================================================
# 🔥 핵심 추가 2: discount_detail 휴리스틱
# =========================================================
def _is_discount_detail_line(text: str) -> bool:
    """
    조건:
    - 끝이 '-' (할인)
    - 또는 -T
    """
    if text.endswith("-"):
        return True

    if text.endswith("-T") or text.endswith("T-"):
        return True

    # 가격인데 음수 표현 포함
    if "-" in text and re.search(r"\d", text):
        return True

    return False


def _is_discount_keyword_line(text: str, store_rules: Any) -> bool:
    normalized = _normalize_space(text).upper()

    for kw in store_rules.get("discount_keywords", []):
        normalized_kw = _normalize_space(kw).upper()
        if normalized == normalized_kw:
            return True

    return False


def _is_discount_target_line(text: str, store_rules: Any) -> bool:
    suffixes = store_rules.get("discount_target_suffix", set())

    if not suffixes:
        return False

    upper_text = _normalize_space(text).upper()

    for suffix in suffixes:
        suffix_upper = str(suffix).strip().upper()

        if upper_text.endswith(" " + suffix_upper):
            return True

        if upper_text.endswith(suffix_upper) and upper_text != suffix_upper:
            return True

    return False


def _matches_any_pattern(text: str, patterns: Iterable[re.Pattern]) -> bool:
    normalized = _normalize_space(text)

    for pattern in patterns:
        if pattern.match(normalized):
            return True

    return False


def _contains_any_keyword(text: str, keywords: Iterable[str]) -> bool:
    normalized_text = _normalize_space(text).upper()

    for kw in keywords:
        normalized_kw = _normalize_space(kw).upper()
        if not normalized_kw:
            continue

        if normalized_kw == normalized_text:
            return True

        if normalized_kw in normalized_text:
            return True

    return False


def _normalize_space(text: str) -> str:
    return " ".join(str(text or "").strip().split())