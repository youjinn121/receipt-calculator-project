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
  - receipt_discount
  - fee
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
3) receipt_discount / fee
4) discount_keyword
5) discount_detail
6) item_detail
7) discount_target
8) fallback → item_name

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
    store = (store or "").lower()

    if not text:
        return "noise"

    # 0) receipt qty
    if _is_receipt_qty_line(text, store_rules):
        return "receipt_qty"

    # 1) noise
    if _is_noise_line(raw, text, store_rules):
        return "noise"

    # 2) subtotal
    if _contains_any_keyword(text, store_rules.get("subtotal_keywords", [])):
        return "subtotal"

    # 3) total
    if _is_total_line(text, store_rules):
        return "total"

    # 4) tax/info
    if _contains_any_keyword(text, store_rules.get("tax_keywords", [])):
        return "noise"

    # 5) receipt_discount / store-specific discount handling

    # hanaro:
    # item 영역 할인 힌트는 receipt_discount보다 먼저 discount_detail로 잡아야 한다.
    # 예: "삼겹 한돈자조금 할인 -1,369"
    if store == "hanaro" and _looks_like_hanaro_body_discount_line(text, store_rules):
        return "discount_detail"

    # 기존 패턴 우선
    if _is_receipt_discount_line(text, store_rules):
        return "receipt_discount"

    # hanaro receipt-level 할인 후보
    # 예: "끝전할인: -4", "쿠폰할인: -660", "총할인액: -4"
    if store == "hanaro" and _looks_like_hanaro_receipt_discount_line(text, store_rules):
        return "receipt_discount"

# emart:

    # emart:
    # body 할인 힌트(에누리/행사/S-POINT)는 우선 discount_detail로 둔다.
    # 실제 receipt_discount 여부는 semantic에서 tail 구간 판단 후 최종 결정.
    if store == "emart" and _looks_like_emart_body_discount_line(text, store_rules):
        return "discount_detail"

    # emart receipt-level 할인 후보
    if store == "emart" and _looks_like_emart_receipt_discount_line(text, store_rules):
        return "receipt_discount"

    # 6) fee
    if _is_fee_line(text, store_rules):
        return "fee"

    # 7) discount keyword
    if _is_discount_keyword_line(text, store_rules):
        return "discount_keyword"

    # 8) discount detail
    if _matches_any_pattern(text, store_rules.get("discount_patterns", [])):
        return "discount_detail"

    # 단독 음수 금액 라인: -6,500 / -2,950 / -10,600
    if _is_standalone_negative_amount_line(text):
        return "discount_detail"

    if _is_discount_detail_line(text):
        return "discount_detail"

    # 9) item detail
    if _matches_any_pattern(text, store_rules.get("item_patterns", [])):
        return "item_detail"

    if _is_item_detail_line(text):
        return "item_detail"

    # 9-1) emart tail-number fallback
    if store == "emart" and _looks_like_item_detail_from_tail_numbers(text):
        return "item_detail"

    # 10) discount target
    if _is_discount_target_line(text, store_rules):
        return "discount_target"

    # 11) fallback
    return "item_name"


# =========================================================
# End-section helper
# parser 메인 루프에서 이 함수가 True면
# 해당 줄까지 저장하고 break 하면 됨
# 우선순위:
# 1) store_rules.total_keywords
# 2) 합계
# 3) 부가세
# 4) 과세
# 5) 면세
# =========================================================
def is_end_section_line(
    text: str,
    store: str | None = None,
    store_rules: Any | None = None,
) -> bool:
    return _get_end_section_priority(text, store=store, store_rules=store_rules) is not None


def _get_end_section_priority(
    text: str,
    store: str | None = None,
    store_rules: Any | None = None,
) -> int | None:
    normalized = _normalize_space(text)

    if store_rules:
        for kw in store_rules.get("total_keywords", []):
            normalized_kw = _normalize_space(kw)
            if normalized_kw and normalized.startswith(normalized_kw):
                return 1

    if normalized.startswith("합계"):
        return 2

    if normalized.startswith("부가세"):
        return 3

    if normalized.startswith("과세"):
        return 4

    if normalized.startswith("면세"):
        return 5

    return None


# =========================================================
# Internal helpers
# =========================================================
def _is_receipt_qty_line(text: str, store_rules: Any) -> bool:
    """
    영수증 전체 상품 수량 라인 판정

    예:
    - 총 품목 수량 15
    - 총상품수량 15
    - 총수량 15

    주의:
    - total 금액 라인 아님
    - noise보다 먼저 잡아야 한다.
    """
    normalized = _normalize_space(text)

    for kw in store_rules.get("receipt_qty_keywords", []):
        normalized_kw = _normalize_space(kw)
        if not normalized_kw:
            continue

        if normalized.startswith(normalized_kw):
            # 키워드 뒤에 수량 숫자가 따라오는 형태만 허용
            if re.search(rf"^{re.escape(normalized_kw)}\s+\d+\s*$", normalized):
                return True

    return False


def _is_noise_line(raw: str, text: str, store_rules: Any) -> bool:
    if _contains_any_keyword(text, store_rules.get("noise_keywords", [])):
        return True

    if _matches_any_pattern(text, store_rules.get("noise_patterns", [])):
        return True

    # Costco OCR 내부 노이즈
    if re.match(r"^\*[A-Z]+", text):
        return True

    if text in {".", "-", "--", "*", "**", "***", ":"}:
        return True

    return False


def _is_total_line(text: str, store_rules: Any) -> bool:
    """
    total 판정

    우선:
    - store_rules.total_keywords 시작 여부

    fallback:
    - '합계' 시작 여부
    """
    normalized = _normalize_space(text)

    for kw in store_rules.get("total_keywords", []):
        normalized_kw = _normalize_space(kw)
        if normalized_kw and normalized.startswith(normalized_kw):
            return True

    return normalized.startswith("합계")


def _is_receipt_discount_line(text: str, store_rules: Any) -> bool:
    if _matches_any_pattern(text, store_rules.get("receipt_discount_patterns", [])):
        return True

    # fallback:
    # 결제할인 : -5,000
    # 카드할인 : -4,000
    if _contains_any_keyword(text, store_rules.get("receipt_discount_keywords", [])):
        if re.search(r":\s*-\s*[\d,]+\s*$", text):
            return True

    return False


def _is_fee_line(text: str, store_rules: Any) -> bool:
    normalized = _normalize_space(text)

    # ---------------------------------------------------------
    # emart 예외:
    # 공병/공 병 라인은 fee로 유지하지 않고 noise로 처리한다.
    # rules에서 noise_keywords로 내리고,
    # 여기서는 fee fallback까지 막아준다.
    # ---------------------------------------------------------
    if str(store_rules.get("store", "")).lower() == "emart":
        if re.match(r"^(공\s*병|공병)\s+[\d,]+$", normalized):
            return False

    if _matches_any_pattern(normalized, store_rules.get("fee_patterns", [])):
        return True

    # fallback
    if re.match(r"^(공\s*병|공병)\s+[\d,]+$", normalized):
        return True

    return False


def _is_item_detail_line(text: str) -> bool:
    """
    fallback 휴리스틱 (Costco 중심)

    조건:
    - 첫 토큰이 4~7자리 숫자 코드
    - 가격 토큰이 2개 이상
    """
    tokens = text.split()

    if len(tokens) < 3:
        return False

    if not re.match(r"^\d{4,7}$", tokens[0]):
        return False

    price_tokens = [t for t in tokens if re.match(r"^[\d,]+$", t)]
    if len(price_tokens) >= 2:
        return True

    return False


def _is_discount_detail_line(text: str) -> bool:
    """
    discount_detail fallback 휴리스틱

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
    # 1) 끝쪽 할인 표식
    # ---------------------------------------------------------
    if re.search(r"[\d,]+(?:-|-T|T-)\s*$", compact):
        return True

    # ---------------------------------------------------------
    # 2) 구조 후보 계산
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
    # 3) 할인 표식 + 구조
    # ---------------------------------------------------------
    has_discount_marker = (
        "-" in compact
        and not re.search(r"-\s*\d", compact)
    )

    if has_discount_marker and structure_score >= 2:
        return True

    return False


def _is_discount_keyword_line(text: str, store_rules: Any) -> bool:
    normalized = _normalize_space(text).upper()

    for kw in store_rules.get("discount_keywords", []):
        normalized_kw = _normalize_space(kw).upper()
        if not normalized_kw:
            continue

        if normalized == normalized_kw:
            return True

        if normalized_kw in normalized:
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


def _looks_like_item_detail_from_tail_numbers(text: str) -> bool:
    """
    item_name fallback 직전 복구용 item_detail 판정

    허용 케이스:
    1) 줄 끝에 [unit_price, qty, total_price] 3개 숫자 토큰이 있고
       unit_price * qty == total_price
    2) 줄 끝에 [unit_price, total_price] 2개 숫자 토큰이 있고
       unit_price == total_price
       -> qty=1 복구 후보

    주의:
    - classifier는 line_type만 결정
    - 실제 qty/name/price 복구는 field_extractor 쪽에서 수행
    """
    tokens = _normalize_space(text).split()
    if len(tokens) < 2:
        return False

    numeric_indices = [
        idx for idx, token in enumerate(tokens)
        if _is_amount_like_token(token)
    ]

    if len(numeric_indices) < 2:
        return False

    # ---------------------------------------------------------
    # case 1) 마지막 3개 숫자 토큰 사용
    # ex) 상품명 11,980 1 11,980
    # ---------------------------------------------------------
    if len(numeric_indices) >= 3:
        last3 = numeric_indices[-3:]

        # 마지막 3개 숫자 토큰이 실제로 연속된 tail인지 확인
        if last3 == list(range(last3[0], last3[0] + 3)):
            unit_price = _parse_amount_token(tokens[last3[0]])
            qty = _parse_qty_token(tokens[last3[1]])
            total_price = _parse_amount_token(tokens[last3[2]])

            if (
                unit_price is not None
                and qty is not None
                and total_price is not None
                and qty >= 1
                and total_price >= unit_price
                and unit_price * qty == total_price
            ):
                return True

    # ---------------------------------------------------------
    # case 2) 마지막 2개 숫자 토큰 사용
    # ex) 상품명 4,820 4,820
    # -> qty=1 복구 후보
    # ---------------------------------------------------------
    last2 = numeric_indices[-2:]
    if last2 == list(range(last2[0], last2[0] + 2)):
        unit_price = _parse_amount_token(tokens[last2[0]])
        total_price = _parse_amount_token(tokens[last2[1]])

        if (
            unit_price is not None
            and total_price is not None
            and unit_price == total_price
        ):
            return True

    return False


def _is_amount_like_token(token: str) -> bool:
    return bool(re.fullmatch(r"[\d,]+", token.strip()))


def _parse_amount_token(token: str) -> int | None:
    stripped = token.strip().replace(",", "")
    if not stripped.isdigit():
        return None
    try:
        return int(stripped)
    except Exception:
        return None


def _parse_qty_token(token: str) -> int | None:
    stripped = token.strip().upper().replace("X", "")
    if not stripped.isdigit():
        return None
    try:
        return int(stripped)
    except Exception:
        return None


def _is_standalone_negative_amount_line(text: str) -> bool:
    """
    예:
    - -6,500
    - -2,950
    - -10,600
    """
    normalized = _normalize_space(text)
    return bool(re.fullmatch(r"-\d[\d,]*", normalized))


def _looks_like_emart_receipt_discount_line(text: str, store_rules: Any) -> bool:
    """
    emart receipt-level 할인 후보
    예:
    - 결제할인 : -5,000
    - 카드할인 : -4,000
    - 삼성카드할인 : 2211101938 -5,000

    주의:
    - 여기서는 line 자체 형태만 판별
    - 실제 '합계 ~ 결제대상금액 사이' 영역 판단은 semantic/tail 처리에서 최종 보강 가능
    """
    normalized = _normalize_space(text)

    if not _contains_any_keyword(
        normalized,
        store_rules.get("receipt_discount_keywords", []),
    ):
        return False

    # 마지막에 음수 금액이 오면 receipt_discount 후보
    if re.search(r"-\s*[\d,]+\s*$", normalized):
        return True

    return False


def _looks_like_emart_body_discount_line(text: str, store_rules: Any) -> bool:
    """
    emart body 영역에서 item 할인 후보로 볼 수 있는 할인 라인 힌트

    예:
    - 포인트에누리행사 -2,500
    - 가공에누리(전점) -2,500
    - 2021 채소 S-POINT -1,500

    주의:
    - 여기서는 line 자체 형태만 본다.
    - 실제 item 귀속 여부는 semantic에서 body 구간인지 확인 후 결정한다.
    """
    normalized = _normalize_space(text)

    hint_keywords = store_rules.get("body_discount_hint_keywords", [])
    if not _contains_any_keyword(normalized, hint_keywords):
        return False

    return bool(re.search(r"-\s*[\d,]+\s*$", normalized))


def _looks_like_hanaro_body_discount_line(text: str, store_rules: Any) -> bool:
    """
    hanaro item-level 할인 후보

    예:
    - 삼겹 한돈자조금 할인 -1,369
    - 삼겹 한돈자조금 할인 -1.369

    주의:
    - receipt_discount보다 먼저 검사해야 한다.
    - "끝전할인", "쿠폰할인", "총할인액"은 영수증 전역 할인으로 처리한다.
    """
    normalized = _normalize_space(text)

    # receipt-level 할인 키워드는 제외
    if _contains_any_keyword(
        normalized,
        store_rules.get("receipt_discount_keywords", []),
    ):
        return False

    hint_keywords = store_rules.get("body_discount_hint_keywords", [])
    if not _contains_any_keyword(normalized, hint_keywords):
        return False

    return bool(re.search(r"-\s*[\d,.]+\s*$", normalized))


def _looks_like_hanaro_receipt_discount_line(text: str, store_rules: Any) -> bool:
    """
    hanaro receipt-level 할인 후보

    예:
    - 끝전할인: -4
    - 끝 전할 인: -1
    - 쿠폰할인: -660
    - 총할인액: -4
    - 농축산물 할인쿠폰 (4월2차) -1,400
    """
    normalized = _normalize_space(text)

    if not _contains_any_keyword(
        normalized,
        store_rules.get("receipt_discount_keywords", []),
    ):
        return False

    return bool(re.search(r"-\s*[\d,.]+\s*$", normalized))