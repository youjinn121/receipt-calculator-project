from __future__ import annotations

import re
from typing import Any, Optional


# =========================================================
# Common regex
# =========================================================

ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")
MULTI_SPACE_RE = re.compile(r"\s+")

COMMA_GROUP_RE = re.compile(r"(\d)\s*,\s*(\d)")
DOT_GROUP_RE = re.compile(r"(\d)\s*\.\s*(\d)")
TRAILING_MINUS_SPACE_RE = re.compile(r"(\d)\s*-\b")
BROKEN_QTY_RE = re.compile(r"(\d)\s+[xX]\b")
QTY_TOKEN_RE = re.compile(r"(\d)\s*[xX]\b")

# 4.000 / 12.900 / 2.500-T 같은 천 단위 점 표기
THOUSAND_DOT_RE = re.compile(r"(?<!\d)([+-]?\d{1,3})\.(\d{3})(?!\d)")

# line 전체 blind 적용은 금지지만, Costco detail 후보에서 안전하게 제거 가능한 케이스만 허용
LEADING_STAR_CODE_RE = re.compile(r"^\*\s*(\d{4,13}\b.*)$")
ITEM_NUMBER_PREFIX_DETAIL_RE = re.compile(r"^\d{2,3}\*(\d{4,13}\b.*)$")

# =========================================================
# Known keyword normalization
# =========================================================

KNOWN_SPACED_KEYWORDS = {
    "끝 전할 인": "끝전할인",
    "부 가 세": "부가세",
    "면세 물품": "면세물품",
    "과세 물품": "과세물품",
    "결 제대상금액": "결제대상금액",
    "제대상금액": "결제대상금액",
    "총 싱품수": "총상품수",
    "총 상품수": "총상품수",
    "총 품목 수량": "총품목수량",
    "합 계": "합계",
}

# Costco 쪽에서 실제 필요했던 오타/변형
COSTCO_KNOWN_VARIANTS = {
    "Sub-총싱품수": "Sub-총상품수",
    "총싱품수": "총상품수",
}

# Costco suffix 토큰은 semantic 연결에 의미가 있으므로 삭제하지 않음
COSTCO_MEANINGFUL_SUFFIXES = {"IRC", "EXM", "PP", "IR"}


# =========================================================
# Public API
# =========================================================

def normalize_line(line_text: str, store: str, store_rules: object | None = None) -> str:
    if line_text is None:
        return ""

    text = str(line_text)
    print(f"[normalize_line][raw] {repr(text)}")

    text = _unicode_and_whitespace_cleanup(text)
    print(f"[normalize_line][after _unicode_and_whitespace_cleanup] {repr(text)}")

    text = _split_number_join(text)
    print(f"[normalize_line][after _split_number_join] {repr(text)}")

    text = _number_separator_normalization(text)
    print(f"[normalize_line][after _number_separator_normalization] {repr(text)}")

    text = _keyword_spacing_normalization(text, store=store)
    print(f"[normalize_line][after _keyword_spacing_normalization] {repr(text)}")

    text = _qty_token_normalization(text)
    print(f"[normalize_line][after _qty_token_normalization] {repr(text)}")

    if _normalize_store(store) == "costco":
        text = _normalize_costco_line_safe(text)
        print(f"[normalize_line][after _normalize_costco_line_safe] {repr(text)}")

    text = re.sub(r"\s+", " ", text)
    
    return text.strip()


def cleanup_name_candidate(text: str, store: str, store_rules: object | None = None) -> str:
    """
    name candidate 전용 정리
    - line 전체에 blind 적용하지 말고
    - name 후보에만 적용
    """
    if text is None:
        return ""

    out = str(text).strip()

    # 번호 prefix 제거: 01 떡붕어싸만코 / 001 P삼겹살
    out = re.sub(r"^(?P<prefix>\d{2,3}\*?)\s+(?P<rest>.+)$", r"\g<rest>", out)

    # 선행 * 제거
    out = re.sub(r"^\*\s*", "", out)

    # 대괄호 태그 제거는 Costco에선 공격적으로 하지 않음
    # suffix(IRC/EXM/PP)는 semantic에서 쓸 수 있으므로 여기서 지우지 않음
    out = _unicode_and_whitespace_cleanup(out)
    return out


def cast_amount_token(token: Any) -> Optional[int]:
    """
    정규화된 숫자 문자열 -> int 후보
    예:
    9,590   -> 9590
    1,800-  -> -1800
    2,600-T -> -2600
    """
    if token is None:
        return None

    if isinstance(token, int):
        return token

    text = str(token).strip()
    if not text:
        return None

    text = _split_number_join(text)
    text = _number_separator_normalization(text)

    text = text.replace(",", "")
    text = re.sub(r"[Tt]$", "", text)

    if text.endswith("-"):
        text = "-" + text[:-1]

    if text.lstrip("+-").isdigit():
        return int(text)

    return None


def cast_discount_amount(token: Any) -> Optional[int]:
    value = cast_amount_token(token)
    if value is None:
        return None
    return abs(value)


def cast_qty_token(token: Any) -> Optional[int]:
    if token is None:
        return None

    if isinstance(token, int):
        return token

    text = str(token).strip()
    if not text:
        return None

    text = text.replace(",", "")
    text = text.replace("X", "x")
    text = text.replace(" ", "")

    if text.endswith("x"):
        text = text[:-1]

    if text.isdigit():
        return int(text)

    return None


# =========================================================
# Internal rule functions
# =========================================================

def _unicode_and_whitespace_cleanup(text: str) -> str:
    text = ZERO_WIDTH_RE.sub("", text)
    text = text.replace("\t", " ")
    text = text.strip()
    text = MULTI_SPACE_RE.sub(" ", text)
    return text


def _split_number_join(text: str) -> str:
    # 10, 790 -> 10,790
    text = COMMA_GROUP_RE.sub(r"\1,\2", text)

    # 1 . 500 -> 1.500
    text = DOT_GROUP_RE.sub(r"\1.\2", text)

    # 1,800 - -> 1,800-
    text = TRAILING_MINUS_SPACE_RE.sub(r"\1-", text)

    # 1 x / 1 X -> 1x
    text = BROKEN_QTY_RE.sub(lambda m: f"{m.group(1)}x", text)

    return text


def _number_separator_normalization(text: str) -> str:
    # 4.000 -> 4,000
    # 12.900 -> 12,900
    # 2.500-T -> 2,500-T
    def repl(m: re.Match) -> str:
        return f"{m.group(1)},{m.group(2)}"

    return THOUSAND_DOT_RE.sub(repl, text)


def _keyword_spacing_normalization(text: str, store: str) -> str:
    for src, dst in KNOWN_SPACED_KEYWORDS.items():
        text = text.replace(src, dst)

    if _normalize_store(store) == "costco":
        for src, dst in COSTCO_KNOWN_VARIANTS.items():
            text = text.replace(src, dst)

    return text


def _qty_token_normalization(text: str) -> str:
    # 1X -> 1x
    text = re.sub(r"(\d)\s*[X]\b", r"\1x", text)

    # 2 x -> 2x
    text = re.sub(r"(\d)\s*x\b", r"\1x", text)

    return text


def _normalize_costco_line_safe(text: str) -> str:
    """
    Costco 전용 안전 정규화
    - detail 후보에서만 말이 되는 선행 prefix 제거
    - suffix(IRC/EXM/PP)는 보존
    """
    # *123456 1 2990 2,990T -> 123456 1 2990 2,990T
    m = LEADING_STAR_CODE_RE.match(text)
    if m:
        text = m.group(1).strip()

    # 001*123456 1 2990 2,990T -> 123456 1 2990 2,990T
    m = ITEM_NUMBER_PREFIX_DETAIL_RE.match(text)
    if m:
        text = m.group(1).strip()

    return text


def _normalize_store(store: str) -> str:
    return str(store or "").strip().lower()