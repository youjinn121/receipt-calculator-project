"""
[Normalizer 역할 정의]

이 모듈은 "문자열 형태 정리"만 담당한다.
절대 의미 해석(semantic)을 수행하지 않는다.

책임 범위:
- 공백/특수문자 정리
- 숫자 포맷 정규화 (예: 10, 790 → 10,790)
- 수량 토큰 정리 (예: 1 x → 1x)
- OCR 깨짐 보정 (예: 총 싱품수 → 총상품수)

금지:
- line_type 판단 금지
- item / discount 생성 금지
- 할인 귀속 처리 금지
- subtotal / total 판단 금지

중요 원칙:
- "패턴 매칭 성공률을 높이기 위한 전처리"까지만 수행
- 의미 정보(IRC, EXM, PP 등)는 절대 제거하지 않는다
- 특히 suffix/prefix(IRC, EXM, PP)는 semantic에서 사용되므로 유지한다

출력:
- normalize_line: 패턴 매칭용 텍스트
- cleanup_name_candidate: name 후보 전용 정리 결과
"""

from __future__ import annotations

import re
from typing import Any, Optional


# =========================================================
# Common regex
# =========================================================

ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")
MULTI_SPACE_RE = re.compile(r"\s+")

# 숫자 내부 분리
COMMA_GROUP_RE = re.compile(r"(\d)\s*,\s*(\d)")
DOT_GROUP_RE = re.compile(r"(\d{1,3})\s*\.\s*(\d{3})(?!\d)")
TRAILING_MINUS_SPACE_RE = re.compile(r"(\d)\s*-\s*$")
BROKEN_QTY_RE = re.compile(r"(\d)\s+[xX]\b")

# 4.000 / 12.900 / 2.500-T 같은 천 단위 점 표기
THOUSAND_DOT_RE = re.compile(r"(?<!\d)([+-]?\d{1,3})\.(\d{3})(?!\d)")

# Costco / Hanaro detail 후보에서 안전하게 제거 가능한 케이스
LEADING_STAR_CODE_RE = re.compile(r"^\*\s*(\d{4,13}\b.*)$")
ITEM_NUMBER_PREFIX_DETAIL_RE = re.compile(r"^\d{2,3}\*(\d{4,13}\b.*)$")

# emart 통합형 이름 후보에서 제거할 prefix
LEADING_ITEM_NO_RE = re.compile(r"^\d{2,3}\*?\s+")
LEADING_BRACKET_PREFIX_RE = re.compile(r"^\([A-Za-z]{1,3}\)")
LEADING_BRACKET_TAG_RE = re.compile(r"^\[[^\]]+\]\s*")

# emart OCR noise:
# 예) "100 %1,590", "50 %2,980"
# 금액 토큰 바로 앞에 끼어든 숫자+% 노이즈 제거용
EMART_PERCENT_NOISE_BEFORE_PRICE_RE = re.compile(
    r"(?P<left>\D|^)(?P<noise>\d{1,3}\s*%)\s*(?P<price>\d{1,3}(?:,\d{3})+)(?=\s+\d+\s+\d{1,3}(?:,\d{3})+\b)"
)

# =========================================================
# Known keyword normalization
# =========================================================

KNOWN_SPACED_KEYWORDS = {
    "끝 전할 인": "끝전할인",
    "부 가 세": "부가세",
    "합 계": "합계",
    "면세 물품": "면세 물품",
    "과세 물품": "과세 물품",
    "결 제대상금액": "결제대상금액",
    "제대상금액": "제대상금액",
    "총 싱품수": "총상품수",
    "총 상품수": "총상품수",
    "총 품목 수량": "총 품목 수량",
    "(*) 면세 물품": "(*)면세 물품",
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

    text = _unicode_and_whitespace_cleanup(text)
    text = _split_number_join(text)
    text = _number_separator_normalization(text)
    text = _keyword_spacing_normalization(text, store=store)
    text = _qty_token_normalization(text)
    text = _sign_spacing_normalization(text)

    normalized_store = _normalize_store(store)

    if normalized_store == "emart":
        text = _normalize_emart_line_safe(text)

    if normalized_store == "costco":
        text = _normalize_costco_line_safe(text)

    if normalized_store == "hanaro":
        text = _normalize_hanaro_line_safe(text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def cleanup_name_candidate(text: str, store: str, store_rules: object | None = None) -> str:
    """
    name candidate 전용 정리
    - line 전체에 blind 적용하지 말고
    - name 후보에만 적용
    - semantic에서 필요한 의미 토큰은 제거하지 않음
    """
    if text is None:
        return ""

    out = str(text).strip()
    if not out:
        return ""

    store_norm = _normalize_store(store)

    # 공통 공백 정리
    out = _unicode_and_whitespace_cleanup(out)

    # 선행 번호 prefix 제거: 01 떡붕어싸만코 / 001 P삼겹살
    out = LEADING_ITEM_NO_RE.sub("", out).strip()

    # 선행 * 제거
    out = re.sub(r"^\*\s*", "", out)

    # emart / hanaro 계열 대괄호 태그 제거
    # ex) [앱]고소미50% / [카드쿠폰(율)]선진 삼겹
    if store_norm in {"emart", "hanaro"}:
        out = LEADING_BRACKET_TAG_RE.sub("", out).strip()

    # emart 이름 앞 괄호 prefix 제거
    # ex) (J)무항생제볶음탕용 / (Ph)돌바나나(송이)
    if store_norm == "emart":
        out = LEADING_BRACKET_PREFIX_RE.sub("", out).strip()

    # store_rules의 name_cleanup_patterns 적용
    if store_rules:
        for pattern in store_rules.get("name_cleanup_patterns", []):
            out = pattern.sub("", out).strip()

    # Costco suffix(IRC/EXM/PP)는 semantic에서 쓰므로 제거하지 않음
    out = _unicode_and_whitespace_cleanup(out)
    return out


def cast_amount_token(token: Any) -> Optional[int]:
    """
    정규화된 숫자 문자열 -> int 후보

    예:
    9,590   -> 9590
    -3,000  -> -3000
    1,800-  -> -1800
    2,600-T -> -2600
    7,990 T -> 7990
    4.000   -> 4000
    """
    if token is None:
        return None

    if isinstance(token, int):
        return token

    text = str(token).strip()
    if not text:
        return None

    text = _unicode_and_whitespace_cleanup(text)
    text = _split_number_join(text)
    text = _number_separator_normalization(text)
    text = _sign_spacing_normalization(text)

    # 중간 공백 제거
    text = re.sub(r"\s+", "", text)

    # trailing tax / discount marker 제거
    text = re.sub(r"[Tt]$", "", text)

    # 1,800- / 2,500-T / 2,500T- -> negative
    if text.endswith("-"):
        text = "-" + text[:-1]
    elif text.endswith("-T") or text.endswith("T-"):
        text = "-" + text[:-2]

    # 남은 T 제거
    text = text.replace("T", "").replace("t", "")

    # 숫자/구분자/부호 외 제거
    text = re.sub(r"[^0-9,.\-+]", "", text)

    if not text or text in {"+", "-"}:
        return None

    # 점(.)과 콤마(,)는 둘 다 천 단위 구분자로 보고 제거
    text = text.replace(",", "").replace(".", "")

    if not text or text in {"+", "-"}:
        return None

    try:
        return int(text)
    except ValueError:
        return None


def cast_discount_amount(token: Any) -> Optional[int]:
    value = cast_amount_token(token)
    if value is None:
        return None
    return abs(value)


def cast_qty_token(token: Any) -> Optional[int]:
    """
    수량 토큰 정규화

    허용:
    - 1
    - 1x
    - 1X
    - 1 x
    - 1 X
    """
    if token is None:
        return None

    if isinstance(token, int):
        return token

    text = str(token).strip()
    if not text:
        return None

    text = _unicode_and_whitespace_cleanup(text)
    text = text.replace(",", "")
    text = text.replace("X", "x")
    text = re.sub(r"\s+", "", text)

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


def _sign_spacing_normalization(text: str) -> str:
    # - 3,000 -> -3,000
    text = re.sub(r"(^|\s)-\s+(\d[\d,\.]*)", r"\1-\2", text)

    # 2,500 -T / 2,500 - T -> 2,500-T
    text = re.sub(r"(\d)\s*-\s*([Tt])\b", r"\1-\2", text)

    # 2,500 T- / 2,500 T - -> 2,500T-
    text = re.sub(r"(\d)\s*([Tt])\s*-\b", r"\1\2-", text)

    # 7,990 T -> 7,990T
    text = re.sub(r"(\d)\s+([Tt])\b", r"\1\2", text)

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


def _normalize_hanaro_line_safe(text: str) -> str:
    """
    Hanaro 전용 안전 정규화
    - *8801045352107 3,060 1 3,060
    - 001*8801448212053 1,680 1 1,680
    같은 detail 후보를 extractor가 읽기 쉽게 정리
    """
    # *8801045352107 ... -> 8801045352107 ...
    m = LEADING_STAR_CODE_RE.match(text)
    if m:
        text = m.group(1).strip()

    # 001*8801448212053 ... -> 8801448212053 ...
    m = ITEM_NUMBER_PREFIX_DETAIL_RE.match(text)
    if m:
        text = m.group(1).strip()

    return text


def _normalize_store(store: str) -> str:
    return str(store or "").strip().lower()


def _normalize_emart_line_safe(text: str) -> str:
    """
    Emart 전용 안전 정규화
    - 금액 영역 바로 앞에 OCR 배경 노이즈로 끼어든 '숫자+%' 패턴 제거
    - 예:
      "* 풀콩나물200G 100 %1,590 1 1,590"
      -> "* 풀콩나물200G 1,590 1 1,590"

    주의:
    - 모든 %를 제거하지 않는다.
    - qty/price 구조가 뒤따르는 item_detail 형태에서만 제한적으로 적용한다.
    - discount/keyword 해석은 하지 않는다.
    """

    def repl(m: re.Match) -> str:
        left = m.group("left")
        price = m.group("price")
        return f"{left}{price}"

    text = EMART_PERCENT_NOISE_BEFORE_PRICE_RE.sub(repl, text)
    return text