"""
[Line Classifier 역할 정의]

이 모듈은 line 단위의 "타입 분류"만 담당한다.

책임 범위:
- line_type 결정
  - item_name
  - item_detail
  - discount_keyword
  - discount_target
  - discount_detail
  - subtotal
  - total
  - noise

금지:
- 값 추출 금지 (code, price 등)
- item 생성 금지
- 할인 귀속 금지
- semantic 해석 금지

분류 우선순위:
1) noise
2) subtotal / total
3) discount_keyword
4) discount_detail
5) item_detail
6) discount_target
7) fallback → item_name

discount_target 규칙:
- suffix: "상품명 IRC", "상품명EXM"
- prefix: "IRC 상품명", "EXM상품명"
- 공백 유무 모두 허용
- 단, 토큰 형태(독립 태그)만 인정 (단순 포함 금지)

주의:
- "IRC 포함"으로 판단하면 안 됨
- 반드시 prefix/suffix 형태만 target으로 인정

출력:
- line_type만 결정 (다른 필드는 extractor에서 처리)
"""

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
    # 반드시 "합계"로 시작하는 경우만 total
    # ex) "합계 375,880", "합계 (VAT 포함) 288,190"
    # 비허용: "쿠폰합계 7 24,200"
    # =========================================================
    if _is_total_line(text):
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
    # 6) discount detail (패턴 우선 + 강화된 휴리스틱)
    # =========================================================
    if _matches_any_pattern(text, store_rules.get("discount_patterns", [])):
        return "discount_detail"

    if _is_discount_detail_line(text):
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
# End-section helper
# parser 메인 루프에서 이 함수가 True면
# 해당 줄까지 저장하고 break 하면 됨
# 우선순위:
# 1) 합계
# 2) 부가세
# 3) 과세
# 4) 면세
# =========================================================
def is_end_section_line(text: str) -> bool:
    return _get_end_section_priority(text) is not None


def _get_end_section_priority(text: str) -> int | None:
    normalized = _normalize_space(text)

    if normalized.startswith("합계"):
        return 1

    if normalized.startswith("부가세"):
        return 2

    if normalized.startswith("과세"):
        return 3

    if normalized.startswith("면세"):
        return 4

    return None


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


def _is_total_line(text: str) -> bool:
    """
    total은 반드시 '합계'로 시작하는 경우만 허용한다.

    허용:
    - 합계 375,880
    - 합계 (VAT 포함) 288,190

    비허용:
    - 쿠폰합계 7 24,200
    """
    normalized = _normalize_space(text)
    return normalized.startswith("합계")


# =========================================================
#  핵심 추가 1: item_detail 휴리스틱
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
#  핵심 추가 2: discount_detail 휴리스틱
# =========================================================
def _is_discount_detail_line(text: str) -> bool:
    """
    discount_detail 휴리스틱 (강화 버전)

    허용 조건:
    1) 숫자-, 숫자-T, T- 같은 끝쪽 할인 표식
    2) 또는 코드/수량/금액 후보 중 2개 이상 + 할인 표식 존재

    금지:
    - 단순히 '-'와 숫자가 같이 있다고 바로 할인으로 보지 않음
      ex) KS새우31-40 908G
    """
    tokens = text.split()
    if not tokens:
        return False

    compact = _normalize_space(text)

    # ---------------------------------------------------------
    # 1) 끝쪽 할인 표식: 숫자-, 숫자-T, 숫자 T-
    # ---------------------------------------------------------
    if re.search(r"[\d,]+(?:-|-T|T-)\s*$", compact):
        return True

    # ---------------------------------------------------------
    # 2) 구조 후보 계산: 코드 / 수량 / 금액
    # ---------------------------------------------------------
    code_candidate = False
    qty_candidate = False
    price_candidate_count = 0

    for token in tokens:
        stripped = token.strip()

        if re.fullmatch(r"\d{4,7}", stripped):
            code_candidate = True

        if re.fullmatch(r"\d+[xX]?", stripped):
            qty_candidate = True

        if re.fullmatch(r"[\d,]+(?:T)?", stripped):
            price_candidate_count += 1

    structure_score = 0
    if code_candidate:
        structure_score += 1
    if qty_candidate:
        structure_score += 1
    if price_candidate_count >= 1:
        structure_score += 1

    # ---------------------------------------------------------
    # 3) 할인 표식이 있고 구조도 어느 정도 갖춘 경우만 허용
    #    단순 -숫자 는 여기서 바로 discount_detail로 보지 않음
    # ---------------------------------------------------------
    has_discount_marker = (
        "-" in compact
        and not re.search(r"-\s*\d", compact)  # 선행 마이너스 금액은 제외
    )

    if has_discount_marker and structure_score >= 2:
        return True

    return False


def _is_discount_keyword_line(text: str, store_rules: Any) -> bool:
    normalized = _normalize_space(text).upper()

    for kw in store_rules.get("discount_keywords", []):
        normalized_kw = _normalize_space(kw).upper()
        if normalized == normalized_kw:
            return True

        if normalized_kw and normalized_kw in normalized:
            return True

    return False


def _is_discount_target_line(text: str, store_rules: Any) -> bool:
    suffixes = store_rules.get("discount_target_suffix", set())
    prefixes = store_rules.get("discount_target_prefix", set())

    if not suffixes and not prefixes:
        return False

    upper_text = _normalize_space(text).upper()
    if not upper_text:
        return False

    tokens = upper_text.split()
    first = tokens[0] if tokens else ""
    last = tokens[-1] if tokens else ""

    # suffix: "상품명 IRC", "상품명IRC"
    for suffix in suffixes:
        s = str(suffix).strip().upper()

        if last == s and len(tokens) > 1:
            return True

        if upper_text.endswith(s) and upper_text != s:
            return True

    # prefix: "IRC 상품명", "IRC상품명"
    for prefix in prefixes:
        p = str(prefix).strip().upper()

        if first == p and len(tokens) > 1:
            return True

        if upper_text.startswith(p) and upper_text != p:
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