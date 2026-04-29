from __future__ import annotations

import ast
import re
from typing import Any, Dict, List, Optional

from receipt_parser.normalizer import normalize_line
from receipt_parser.line_classifier import classify_line, is_end_section_line
from receipt_parser.field_extractor import extract_fields
from receipt_parser.store_rules import get_store_rules
from receipt_parser.field_recovery import recover_fields


def infer_store_from_filename(file_name: str) -> Optional[str]:
    """
    개발/테스트용 fallback.
    실제 서비스에서는 store를 명시적으로 받는 것이 우선이다.
    """
    lower = (file_name or "").lower()

    if "costco" in lower:
        return "costco"
    if "emart" in lower:
        return "emart"
    if "hanaro" in lower:
        return "hanaro"

    return None


def _safe_literal_eval(value: str) -> Any:
    try:
        return ast.literal_eval(value)
    except Exception:
        return value


def _unwrap_nested_line_text(value: Any, max_depth: int = 5) -> Any:
    """
    중첩된 dict-string / dict / parser output 구조에서
    실제 line_text까지 최대 max_depth 단계로 내려간다.

    예:
    "{'line_idx': 10, 'line_text': \"{'line_idx': 10, 'line_text': '650635 1x 9,590 9,590', ...}\" ...}"
      -> "650635 1x 9,590 9,590"
    """
    current = value

    for _ in range(max_depth):
        # 1) 문자열인데 dict/list처럼 생겼으면 literal_eval 시도
        if isinstance(current, str):
            stripped = current.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                parsed = _safe_literal_eval(stripped)
                if parsed is current:
                    break
                current = parsed
                continue
            break

        # 2) dict면 line_text 우선
        if isinstance(current, dict):
            if "line_text" in current:
                next_value = current.get("line_text")
                if next_value == current:
                    break
                current = next_value
                continue

            # token dict인 경우
            if "text" in current:
                return str(current.get("text", "")).strip()

            break

        # 3) list는 그대로 반환해서 상위에서 처리
        if isinstance(current, list):
            return current

        break

    return current


def line_to_plain_text(line: Any) -> str:
    """
    입력 line을 실제 분류/추출에 사용할 plain text로 변환한다.

    지원 형태:
    1) 이미 str
    2) dict-string (심지어 중첩된 dict-string도 처리)
    3) dict with line_text
    4) token list
    5) parser intermediate dict
    """
    if line is None:
        return ""

    unwrapped = _unwrap_nested_line_text(line)

    # 최종적으로 다시 한 번 dict/list일 수 있음
    if isinstance(unwrapped, dict):
        if "line_text" in unwrapped:
            return line_to_plain_text(unwrapped.get("line_text"))
        if "text" in unwrapped:
            return str(unwrapped.get("text", "")).strip()
        return str(unwrapped).strip()

    if isinstance(unwrapped, str):
        return unwrapped.strip()

    if isinstance(unwrapped, list):
        texts: List[str] = []

        for token in unwrapped:
            token_unwrapped = _unwrap_nested_line_text(token)

            if isinstance(token_unwrapped, dict):
                if "text" in token_unwrapped:
                    text = str(token_unwrapped.get("text", "")).strip()
                elif "line_text" in token_unwrapped:
                    text = line_to_plain_text(token_unwrapped.get("line_text"))
                else:
                    text = str(token_unwrapped).strip()
            else:
                text = str(token_unwrapped).strip()

            if text:
                texts.append(text)

        return _smart_join_tokens(texts)

    return str(unwrapped).strip()


def _smart_join_tokens(tokens: List[str]) -> str:
    """
    토큰 병합
    - 한글 분절 복원: 아보카 + 도 -> 아보카도
    - 숫자+한글 단위 복원: 6 + 개 -> 6개
    """
    if not tokens:
        return ""

    result = [tokens[0]]

    for token in tokens[1:]:
        if not token:
            continue

        prev = result[-1]

        if not prev:
            result[-1] = token
            continue

        # 숫자 + 한글 단위
        if prev.isdigit() and _is_korean(token[0]):
            result[-1] = prev + token
            continue

        # 한글 + 한글 분절
        if _is_korean(prev[-1]) and _is_korean(token[0]):
            result[-1] = prev + token
            continue

        result.append(token)

    return " ".join(result)


def _is_korean(ch: str) -> bool:
    return "가" <= ch <= "힣"


def build_structured_line(
    line_idx: int,
    line_text: str,
    normalized_line_text: str,
    line_type: str,
    extracted: Dict[str, Any],
) -> Dict[str, Any]:
    """
    최종 line 단위 구조화 결과 생성
    """
    return {
        "line_idx": line_idx,
        "line_text": line_text,
        "normalized_line_text": normalized_line_text,
        "line_type": line_type,
        "code": extracted.get("code"),
        "qty": extracted.get("qty"),
        "unit_price_raw": extracted.get("unit_price_raw"),
        "price_raw": extracted.get("price_raw"),
        "discount_raw": extracted.get("discount_raw"),
        "name_raw": extracted.get("name_raw"),
        "subtotal_count": extracted.get("subtotal_count"),
        "receipt_qty": extracted.get("receipt_qty"),
        "is_restored": extracted.get("is_restored", False),
        "restore_reason": extracted.get("restore_reason"),
        "restored_fields": extracted.get("restored_fields", []),
    }


def parse_single_line(
    raw_line: Any,
    line_idx: int,
    store: str,
    store_rules: Dict[str, Any],
) -> Dict[str, Any]:
    """
    line 하나를
    - plain text 변환
    - normalize
    - classify
    - extract
    순서로 처리한다.
    """
    line_text = line_to_plain_text(raw_line)

    normalized_line_text = normalize_line(
        line_text=line_text,
        store=store,
        store_rules=store_rules,
    )

    line_type = classify_line(
        line_text=line_text,
        normalized_line_text=normalized_line_text,
        store=store,
        store_rules=store_rules,
    )

    extracted = extract_fields(
        line_text=line_text,
        normalized_line_text=normalized_line_text,
        line_type=line_type,
        store=store,
        store_rules=store_rules,
    )

    extracted = recover_fields(
        line_text=line_text,
        normalized_line_text=normalized_line_text,
        line_type=line_type,
        extracted=extracted,
        store=store,
        store_rules=store_rules,
    )

    return build_structured_line(
        line_idx=line_idx,
        line_text=line_text,
        normalized_line_text=normalized_line_text,
        line_type=line_type,
        extracted=extracted,
    )


def parse_lines(
    lines: List[Any],
    store: str,
    store_rules: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    줄 리스트를 받아 structured lines 반환
    """
    if store_rules is None:
        store_rules = get_store_rules(store)

    structured_lines: List[Dict[str, Any]] = []

    for idx, raw_line in enumerate(lines):
        row = parse_single_line(
            raw_line=raw_line,
            line_idx=idx,
            store=store,
            store_rules=store_rules,
        )
        structured_lines.append(row)

    return structured_lines


def recover_hanaro_split_price_qty_lines(
    structured_lines: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    hanaro OCR split 복원

    예:
    007 P청양 700 1
    *232046 700

    ->
    item_name: P청양
    item_detail: code=232046, unit_price=700, qty=1, price_raw=700
    """

    recovered_lines = [dict(row) for row in structured_lines]

    for idx in range(len(recovered_lines) - 1):
        current = recovered_lines[idx]
        next_row = recovered_lines[idx + 1]

        if current.get("line_type") != "item_name":
            continue

        if next_row.get("line_type") != "item_name":
            continue

        current_text = str(
            current.get("normalized_line_text")
            or current.get("line_text")
            or ""
        ).strip()

        next_text = str(
            next_row.get("normalized_line_text")
            or next_row.get("line_text")
            or ""
        ).strip()

        # 현재 줄: 007 P청양 700 1
        current_match = re.match(
            r"^(?P<seq>\d{3})\s+"
            r"(?P<name>.+?)\s+"
            r"(?P<unit_price>\d{1,3}(?:,\d{3})*|\d+)\s+"
            r"(?P<qty>\d+)$",
            current_text,
        )

        # 다음 줄: *232046 700 또는 232046 700
        next_match = re.match(
            r"^\*?\s*"
            r"(?P<code>\d{4,13})\s+"
            r"(?P<price>\d{1,3}(?:,\d{3})*|\d+)$",
            next_text,
        )

        if not current_match or not next_match:
            continue

        name = current_match.group("name").strip()
        unit_price = _parse_amount(current_match.group("unit_price"))
        qty = int(current_match.group("qty"))
        code = next_match.group("code")
        price = _parse_amount(next_match.group("price"))

        if unit_price is None or price is None:
            continue

        if unit_price * qty != price:
            continue

        # 현재 줄은 순수 item_name으로 정리
        current["name_raw"] = name
        current["normalized_line_text"] = f"{current_match.group('seq')} {name}"
        current["is_restored"] = True
        current["restore_reason"] = "hanaro split item_name detail tokens removed"
        current["restored_fields"] = _append_restored_fields(
            current.get("restored_fields", []),
            ["name_raw", "normalized_line_text"],
        )

        # 다음 줄은 item_detail로 복원
        next_row["line_type"] = "item_detail"
        next_row["code"] = code
        next_row["qty"] = qty
        next_row["unit_price_raw"] = unit_price
        next_row["price_raw"] = price
        next_row["discount_raw"] = None
        next_row["name_raw"] = None
        next_row["is_restored"] = True
        next_row["restore_reason"] = "hanaro split item_detail recovered from previous item_name"
        next_row["restored_fields"] = _append_restored_fields(
            next_row.get("restored_fields", []),
            ["line_type", "code", "unit_price_raw", "qty", "price_raw"],
        )

        recovered_lines[idx] = current
        recovered_lines[idx + 1] = next_row

    return recovered_lines


def _parse_amount(value: Any) -> Optional[int]:
    if value is None:
        return None

    text = str(value).strip().replace(",", "").replace(".", "")

    if not text.isdigit():
        return None

    return int(text)


def _append_restored_fields(
    current: List[str],
    fields: List[str],
) -> List[str]:
    result = list(current or [])

    for field in fields:
        if field not in result:
            result.append(field)

    return result


def resolve_store(
    receipt: Dict[str, Any],
    store: Optional[str] = None,
) -> str:
    """
    store 결정 우선순위:
    1. 함수 인자 store
    2. receipt["store"]
    3. file_name 기반 fallback
    """
    if store is not None:
        return str(store).strip().lower()

    receipt_store = receipt.get("store")
    if receipt_store:
        return str(receipt_store).strip().lower()

    file_name = receipt.get("file_name", "")
    inferred = infer_store_from_filename(file_name)
    if inferred:
        return inferred

    raise ValueError(
        f"스토어 추론 실패: file_name={receipt.get('file_name', '')!r}. "
        "parse_receipt(..., store='costco')처럼 명시적으로 전달해야 합니다."
    )


def parse_receipt(
    receipt: Dict[str, Any],
    store: Optional[str] = None,
) -> Dict[str, Any]:
    """
    receipt 단위 파싱
    """
    resolved_store = resolve_store(receipt, store=store)
    store_rules = get_store_rules(resolved_store)
    lines = receipt.get("lines", [])

    trimmed_start_lines = trim_lines_from_start_section(
        lines=lines,
        store=resolved_store,
        store_rules=store_rules,
    )

    trimmed_lines = trim_lines_before_end_section(
        lines=trimmed_start_lines,
        store=resolved_store,
        store_rules=store_rules,
    )

    structured_lines = parse_lines(
        lines=trimmed_lines,
        store=resolved_store,
        store_rules=store_rules,
    )

    if resolved_store == "hanaro":
        structured_lines = recover_hanaro_split_price_qty_lines(structured_lines)

    return {
        "file_name": receipt.get("file_name", ""),
        "file_meta": receipt.get("file_meta", {}),
        "store": resolved_store,
        "lines": structured_lines,
    }



def trim_lines_before_end_section(
    lines: List[Any],
    store: str,
    store_rules: Dict[str, Any],
) -> List[Any]:
    """
    종료 포인트가 발견되면 그 줄까지 포함하고 이후 라인은 잘라낸다.

    emart 종료 우선순위:
    1) 결제대상금액 / 제대상금액
    2) 합계 뒤에 이어지는 receipt-level 할인 마지막 줄
    3) 합계
    4) subtotal fallback
    5) 없으면 원본 유지

    그 외 store:
    - 기존처럼 is_end_section_line() 기준 마지막 종료 라인
    - 없으면 subtotal fallback
    """
    if not lines:
        return lines

    normalized_lines: List[str] = []
    for raw_line in lines:
        plain = line_to_plain_text(raw_line)
        normalized = normalize_line(
            line_text=plain,
            store=store,
            store_rules=store_rules,
        )
        normalized_lines.append(normalized)

    store = str(store or "").strip().lower()

    if store == "emart":
        end_idx = _find_emart_end_idx(
            normalized_lines=normalized_lines,
            store_rules=store_rules,
        )
    elif store == "hanaro":
        end_idx = _find_hanaro_end_idx(
            normalized_lines=normalized_lines,
            store_rules=store_rules,
        )
    else:
        end_idx: Optional[int] = None

        # 1) total/tax 종료 포인트 우선
        for idx, normalized in enumerate(normalized_lines):
            if is_end_section_line(
                text=normalized,
                store=store,
                store_rules=store_rules,
            ):
                end_idx = idx

        # 2) subtotal 마지막 위치 fallback
        if end_idx is None:
            subtotal_keywords = store_rules.get("subtotal_keywords", [])
            for idx, normalized in enumerate(normalized_lines):
                if _contains_any_keyword(normalized, subtotal_keywords):
                    end_idx = idx

    if end_idx is None:
        return lines

    return lines[: end_idx + 1]


def _contains_any_keyword(text: str, keywords: List[str] | set[str]) -> bool:
    normalized_text = " ".join(str(text or "").strip().split()).upper()

    for kw in keywords:
        normalized_kw = " ".join(str(kw or "").strip().split()).upper()
        if not normalized_kw:
            continue

        if normalized_kw == normalized_text:
            return True

        if normalized_kw in normalized_text:
            return True

    return False


def _find_emart_end_idx(
    normalized_lines: List[str],
    store_rules: Dict[str, Any],
) -> Optional[int]:
    """
    emart 종료 포인트 선택

    우선순위:
    1) 결제대상금액 / 제대상금액 마지막 위치
    2) 합계 뒤에 이어지는 receipt-level 할인 마지막 위치
    3) 합계 마지막 위치
    4) subtotal 마지막 위치
    """
    payment_total_idx: Optional[int] = None
    receipt_discount_idx: Optional[int] = None
    sum_idx: Optional[int] = None
    subtotal_idx: Optional[int] = None

    total_keywords = store_rules.get("total_keywords", [])
    subtotal_keywords = store_rules.get("subtotal_keywords", [])

    for idx, normalized in enumerate(normalized_lines):
        if _starts_with_any_keyword(normalized, total_keywords):
            payment_total_idx = idx

        if _is_emart_receipt_discount_candidate(normalized):
            receipt_discount_idx = idx

        if normalized.startswith("합계"):
            sum_idx = idx

        if _contains_any_keyword(normalized, subtotal_keywords):
            subtotal_idx = idx

    # 1) 결제대상금액이 있으면 최우선
    if payment_total_idx is not None:
        return payment_total_idx

    # 2) 합계 뒤에 receipt-level 할인 라인이 이어진 경우
    if (
        sum_idx is not None
        and receipt_discount_idx is not None
        and receipt_discount_idx > sum_idx
    ):
        return receipt_discount_idx

    # 3) 일반 합계
    if sum_idx is not None:
        return sum_idx

    # 4) subtotal fallback
    if subtotal_idx is not None:
        return subtotal_idx

    return None


def _is_emart_receipt_discount_candidate(text: str) -> bool:
    """
    emart 영수증 하단 전역 할인 후보

    예:
    - 결제할인 : 2201606006 -4,410
    - 삼성카드할인 : 2211101938 -5,000
    - [앱]룰렛3천원 : 2201606243 -3,000
    - 15%할인 : 2201606094 - 3,000
    """
    normalized = " ".join(str(text or "").strip().split())

    if re.match(r"^.+할인\s*:\s*\d+\s*-\s*[\d,]+$", normalized):
        return True

    if re.match(r"^\[앱\].+:\s*\d+\s*-\s*[\d,]+$", normalized):
        return True

    return False


def _starts_with_any_keyword(text: str, keywords: List[str] | set[str]) -> bool:
    normalized_text = " ".join(str(text or "").strip().split()).upper()

    for kw in keywords:
        normalized_kw = " ".join(str(kw or "").strip().split()).upper()
        if not normalized_kw:
            continue

        if normalized_text.startswith(normalized_kw):
            return True

    return False


def trim_lines_from_start_section(
    lines: List[Any],
    store: str,
    store_rules: Dict[str, Any],
) -> List[Any]:
    """
    시작 포인트 이전 라인을 잘라낸다.

    emart만 적용
    """
    if not lines:
        return lines

    store = str(store or "").strip().lower()

    if store == "emart":
        start_idx = _find_emart_start_idx(
            lines=lines,
            store=store,
            store_rules=store_rules,
        )
    elif store == "hanaro":
        start_idx = _find_hanaro_start_idx(
            lines=lines,
            store=store,
            store_rules=store_rules,
        )
    else:
        return lines

    if start_idx is None:
        return lines

    return lines[start_idx:]


def _find_emart_start_idx(
    lines: List[Any],
    store: str,
    store_rules: Dict[str, Any],
) -> Optional[int]:
    """
    emart 시작 포인트 찾기

    후보:
    - 상품명 단 가 수량 금 액
    - 단 가 수량 금 액
    - 상품코드 단 가 수량 금 액
    """
    start_candidates = [
        "상품명 단 가 수량 금 액",
        "단 가 수량 금 액",
        "상품코드 단 가 수량 금 액",
    ]

    normalized_candidates = [
        _normalize_for_compare(c) for c in start_candidates
    ]

    for idx, raw_line in enumerate(lines):
        plain = line_to_plain_text(raw_line)

        normalized = normalize_line(
            line_text=plain,
            store=store,
            store_rules=store_rules,
        )

        normalized_text = _normalize_for_compare(normalized)

        for candidate in normalized_candidates:
            if normalized_text == candidate:
                return idx

    return None


def _normalize_for_compare(text: str) -> str:
    """
    비교용 정규화
    - 공백 제거
    - 대문자 통일
    """
    return "".join(str(text or "").strip().upper().split())

def _find_hanaro_end_idx(
    normalized_lines: List[str],
    store_rules: Dict[str, Any],
) -> Optional[int]:
    """
    hanaro 종료 포인트 선택

    우선순위:
    1) 내실금액 마지막 위치
    2) 내실금액 뒤 receipt-level 할인/총할인액이 이어지면 그 마지막 위치
    3) 총구매액 마지막 위치 fallback

    예:
    - 총구매액: 30,400
    - 끝전할인: -4
    - 총할인액: -4
    - 내실금액: 30,400
    """
    total_idx: Optional[int] = None
    subtotal_idx: Optional[int] = None
    receipt_discount_idx: Optional[int] = None

    total_keywords = store_rules.get("total_keywords", [])
    subtotal_keywords = store_rules.get("subtotal_keywords", [])
    receipt_discount_keywords = store_rules.get("receipt_discount_keywords", [])

    for idx, normalized in enumerate(normalized_lines):
        if _starts_with_any_keyword(normalized, total_keywords):
            total_idx = idx

        if _contains_any_keyword(normalized, subtotal_keywords):
            subtotal_idx = idx

        if _is_hanaro_receipt_discount_candidate(
            normalized,
            receipt_discount_keywords=receipt_discount_keywords,
        ):
            receipt_discount_idx = idx

    # 내실금액이 있으면 최종 결제금액 기준으로 종료
    if total_idx is not None:
        # total 뒤에 receipt_discount/총할인액 같은 요약 라인이 더 있으면 거기까지 포함
        if receipt_discount_idx is not None and receipt_discount_idx > total_idx:
            return receipt_discount_idx
        return total_idx

    # 내실금액이 없고, 총구매액 이후 receipt_discount가 있으면 그 라인까지 포함
    if (
        subtotal_idx is not None
        and receipt_discount_idx is not None
        and receipt_discount_idx > subtotal_idx
    ):
        return receipt_discount_idx

    # fallback: 총구매액
    if subtotal_idx is not None:
        return subtotal_idx

    return None


def _is_hanaro_receipt_discount_candidate(
    text: str,
    receipt_discount_keywords: List[str] | set[str],
) -> bool:
    """
    hanaro 영수증 하단 전역 할인 후보

    예:
    - 끝전할인: -4
    - 끝전할인 -4
    - 끝전할 인: -1
    - 쿠폰할인: -660
    - 총할인액: -4
    - 농축산물 할인쿠폰 (4월2차) -1,400
    """
    normalized = " ".join(str(text or "").strip().split())

    if not _contains_any_keyword(normalized, receipt_discount_keywords):
        return False

    return bool(re.search(r"-\s*[\d,.]+\s*$", normalized))


def _find_hanaro_start_idx(
    lines: List[Any],
    store: str,
    store_rules: Dict[str, Any],
) -> Optional[int]:
    """
    hanaro 시작 포인트 찾기

    후보:
    - 상품(코드) 단가 수량 금액
    - 상품코드 단가 수량 금액
    - 상품명 단가 수량 금액
    - 단가 수량 금액

    헤더가 없으면 첫 item_detail 후보 라인 직전까지는 유지하지 않고,
    첫 item_detail 앞의 상품명 라인을 살리기 위해 item_detail 발견 시 max(idx-1, 0)을 반환.
    """
    start_candidates = [
        "상품(코드) 단가 수량 금액",
        "상품코드 단가 수량 금액",
        "상품명 단가 수량 금액",
        "단가 수량 금액",
    ]

    normalized_candidates = [
        _normalize_for_compare(c) for c in start_candidates
    ]

    normalized_lines: List[str] = []

    for idx, raw_line in enumerate(lines):
        plain = line_to_plain_text(raw_line)

        normalized = normalize_line(
            line_text=plain,
            store=store,
            store_rules=store_rules,
        )
        normalized_lines.append(normalized)

        normalized_text = _normalize_for_compare(normalized)

        for candidate in normalized_candidates:
            if normalized_text == candidate:
                # 헤더 다음 줄부터 시작
                return idx + 1

    # header가 없을 때 fallback:
    # 첫 item_detail 라인을 찾고, 바로 앞 상품명 라인을 같이 살림
    for idx, normalized in enumerate(normalized_lines):
        if _matches_any_pattern(normalized, store_rules.get("item_patterns", [])):
            return max(idx - 1, 0)

    return None


def _matches_any_pattern(text: str, patterns: List[re.Pattern] | set[re.Pattern]) -> bool:
    normalized = " ".join(str(text or "").strip().split())

    for pattern in patterns:
        if pattern.match(normalized):
            return True

    return False
