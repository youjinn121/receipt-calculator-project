from __future__ import annotations

import ast
from typing import Any, Dict, List, Optional

from receipt_parser.normalizer import normalize_line
from receipt_parser.line_classifier import classify_line
from receipt_parser.field_extractor import extract_fields
from receipt_parser.store_rules import get_store_rules


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
) -> List[Dict[str, Any]]:
    """
    줄 리스트를 받아 structured lines 반환
    """
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
    lines = receipt.get("lines", [])

    structured_lines = parse_lines(
        lines=lines,
        store=resolved_store,
    )

    return {
        "file_name": receipt.get("file_name", ""),
        "file_meta": receipt.get("file_meta", {}),
        "store": resolved_store,
        "lines": structured_lines,
    }


def parse_receipts(
    receipts: List[Dict[str, Any]],
    store: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    여러 receipt 처리
    """
    results: List[Dict[str, Any]] = []

    for receipt in receipts:
        parsed = parse_receipt(receipt, store=store)
        results.append(parsed)

    return results