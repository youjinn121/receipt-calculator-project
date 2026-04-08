from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# =========================================================
# Recovery config
# =========================================================

DEFAULT_MAX_INFERRED_QTY_BY_STORE = {
    "emart": 9,
    "hanaro": 9,
    "costco": 20,
}

NOISE_CHARS_IN_QTY = {"|", "!", "I", "l", ".", " "}
NOISE_CHARS_IN_NUMERIC = {"|", "!", "I", "l", " ", "%"}
NUMERIC_LIKE_TOKEN_RE = re.compile(r"[+-]?\d[\d,|!Il\.%]*x?", re.IGNORECASE)

CONFUSABLE_DIGIT_PAIRS = {
    ("8", "3"), ("3", "8"),
    ("5", "6"), ("6", "5"),
    ("1", "7"), ("7", "1"),
    ("0", "8"), ("8", "0"),
    ("0", "6"), ("6", "0"),
    ("2", "7"), ("7", "2"),
}

# =========================================================
# Public API
# =========================================================

def recover_fields(
    *,
    line_text: str,
    normalized_line_text: str,
    line_type: str,
    extracted: Dict[str, Any],
    store: str,
    store_rules: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    extractor 이후 단계에서 U/Q/P(field triplet)를 조건부 복구한다.

    원칙:
    - item_detail에만 적용
    - 무조건 덮어쓰기 금지
    - U/Q/P 중 2개를 anchor로 삼아 나머지 1개만 복구
    - 복구가 애매하면 원문 유지
    """
    result = dict(extracted or {})
    store_norm = str(store or "").strip().lower()

    # recovery meta 기본값 보장
    result.setdefault("is_restored", False)
    result.setdefault("restore_reason", None)
    result.setdefault("restored_fields", [])
    result.setdefault("recovery_confidence", None)

    if line_type != "item_detail":
        return result

    qty = _safe_int(result.get("qty"))
    unit_price = _safe_int(result.get("unit_price_raw"))
    price = _safe_int(result.get("price_raw"))

    tokens = _extract_numeric_like_tokens(normalized_line_text or line_text or "")
    raw_triplet = _infer_raw_triplet_tokens(tokens)

    qty_raw = raw_triplet.get("qty_raw")
    unit_raw = raw_triplet.get("unit_price_raw")
    price_raw = raw_triplet.get("price_raw")

    # ---------------------------------------------------------
    # Hypothesis 1: qty가 깨졌을 것이다
    # Anchor: unit_price + price
    # ---------------------------------------------------------
    qty_recovered = _recover_qty_from_unit_and_price(
        qty=qty,
        unit_price=unit_price,
        price=price,
        qty_raw=qty_raw,
        store=store_norm,
    )
    if qty_recovered is not None:
        qty = qty_recovered["value"]
        result["qty"] = qty
        _apply_recovery_meta(
            result=result,
            field_name="qty",
            reason=qty_recovered["reason"],
            confidence=qty_recovered["confidence"],
        )

    # ---------------------------------------------------------
    # Hypothesis 2: unit_price가 깨졌을 것이다
    # Anchor: qty + price
    # ---------------------------------------------------------
    unit_recovered = _recover_unit_price_from_qty_and_price(
        unit_price=unit_price,
        qty=qty,
        price=price,
        unit_raw=unit_raw,
    )
    if unit_recovered is not None:
        unit_price = unit_recovered["value"]
        result["unit_price_raw"] = unit_price
        _apply_recovery_meta(
            result=result,
            field_name="unit_price_raw",
            reason=unit_recovered["reason"],
            confidence=unit_recovered["confidence"],
        )

    # ---------------------------------------------------------
    # Hypothesis 3: price가 깨졌을 것이다
    # Anchor: unit_price + qty
    #
    # 주의:
    # - 단순 mismatch라고 바로 덮어쓰지 않는다.
    # - missing deduction 또는 강한 노이즈 흔적이 있을 때만 복구
    # ---------------------------------------------------------
    price_recovered = _recover_price_from_unit_and_qty(
        
        price=price,
        unit_price=unit_price,
        qty=qty,
        price_raw=price_raw,
    )
    if "602025" in (normalized_line_text or line_text or ""):
        print("[RECOVERY DEBUG]")
        print("line_text:", line_text)
        print("normalized_line_text:", normalized_line_text)
        print("qty:", qty)
        print("unit_price:", unit_price)
        print("price:", price)
        print("price_raw_token:", price_raw)
        print("expected_price:", (unit_price * qty) if isinstance(unit_price, int) and isinstance(qty, int) else None)
        print("confusable_check:", _is_confusable_single_digit_substitution(price, unit_price * qty) if isinstance(price, int) and isinstance(unit_price, int) and isinstance(qty, int) else None)
        print("price_recovered:", price_recovered)
    if price_recovered is not None:
        price = price_recovered["value"]
        result["price_raw"] = price
        _apply_recovery_meta(
            result=result,
            field_name="price_raw",
            reason=price_recovered["reason"],
            confidence=price_recovered["confidence"],
        )

    return result


# =========================================================
# Hypothesis handlers
# =========================================================

def _recover_qty_from_unit_and_price(
    *,
    qty: Optional[int],
    unit_price: Optional[int],
    price: Optional[int],
    qty_raw: Optional[str],
    store: str,
) -> Optional[Dict[str, Any]]:
    if not isinstance(unit_price, int) or not isinstance(price, int):
        return None
    if unit_price <= 0 or price <= 0:
        return None
    if price % unit_price != 0:
        return None

    expected_qty = price // unit_price
    max_inferred_qty = DEFAULT_MAX_INFERRED_QTY_BY_STORE.get(store, 9)

    # blind deduction: qty 누락
    if qty is None:
        if 1 <= expected_qty <= max_inferred_qty:
            return {
                "value": expected_qty,
                "reason": "qty_missing_deduction",
                "confidence": "medium",
            }
        return None

    # 이미 맞으면 복구 불필요
    if qty == expected_qty:
        return None

    # sticky noise correction:
    # ex) qty_raw=21, expected_qty=2
    # ex) qty_raw=2|, expected_qty=2
    # ex) qty_raw=2I, expected_qty=2
    if _qty_raw_supports_expected(qty_raw=qty_raw, expected_qty=expected_qty):
        return {
            "value": expected_qty,
            "reason": "qty_noise_correction",
            "confidence": "high",
        }

    return None


def _recover_unit_price_from_qty_and_price(
    *,
    unit_price: Optional[int],
    qty: Optional[int],
    price: Optional[int],
    unit_raw: Optional[str],
) -> Optional[Dict[str, Any]]:
    if not isinstance(qty, int) or not isinstance(price, int):
        return None
    if qty <= 0 or price <= 0:
        return None
    if price % qty != 0:
        return None

    expected_unit_price = price // qty
    if expected_unit_price <= 0:
        return None

    # blind deduction: unit_price 누락
    if unit_price is None:
        return {
            "value": expected_unit_price,
            "reason": "unit_price_missing_deduction",
            "confidence": "medium",
        }

    # 이미 맞으면 복구 불필요
    if unit_price == expected_unit_price:
        return None

    # noise correction:
    # ex) "100 %1,590" -> 1590
    if _numeric_raw_supports_expected(raw_token=unit_raw, expected_value=expected_unit_price):
        return {
            "value": expected_unit_price,
            "reason": "unit_price_noise_correction",
            "confidence": "high",
        }

    return None


def _recover_price_from_unit_and_qty(
    *,
    price: Optional[int],
    unit_price: Optional[int],
    qty: Optional[int],
    price_raw: Optional[str],
) -> Optional[Dict[str, Any]]:
    if not isinstance(unit_price, int) or not isinstance(qty, int):
        return None
    if unit_price <= 0 or qty <= 0:
        return None

    expected_price = unit_price * qty


    # ---------------------------------------------------------
    # 1) blind deduction: price 누락
    # ---------------------------------------------------------
    if price is None:
        return {
            "value": expected_price,
            "reason": "price_missing_deduction",
            "confidence": "medium",
        }

    # 이미 맞으면 복구 불필요
    if price == expected_price:
        return None

    # ---------------------------------------------------------
    # 2) qty == 1 이면 unit_price == total_price일 가능성이 매우 높다.
    #    단, 아무 1글자 차이나 허용하지 않고
    #    OCR 혼동쌍일 때만 복구 허용
    # ---------------------------------------------------------
    if qty == 1:
        if _is_confusable_single_digit_substitution(price, expected_price):
            return {
                "value": expected_price,
                "reason": "price_noise_correction_confusable_digit",
                "confidence": "medium",
            }

    # ---------------------------------------------------------
    # 3) 매우 보수적 raw pattern 기반 복구
    #    단순 mismatch라고 바로 덮어쓰지 않는다.
    # ---------------------------------------------------------
    if _price_raw_supports_expected(raw_token=price_raw, expected_value=expected_price):
        return {
            "value": expected_price,
            "reason": "price_noise_correction",
            "confidence": "low",
        }

    return None


# =========================================================
# Recovery helpers
# =========================================================

def _apply_recovery_meta(
    *,
    result: Dict[str, Any],
    field_name: str,
    reason: str,
    confidence: str,
) -> None:
    restored_fields = list(result.get("restored_fields") or [])

    if field_name not in restored_fields:
        restored_fields.append(field_name)

    result["restored_fields"] = restored_fields
    result["is_restored"] = True

    existing_reason = result.get("restore_reason")
    if not existing_reason:
        result["restore_reason"] = reason
    elif reason not in str(existing_reason):
        result["restore_reason"] = f"{existing_reason}; {reason}"

    # confidence는 더 높은 쪽 유지
    existing_confidence = result.get("recovery_confidence")
    result["recovery_confidence"] = _max_confidence(existing_confidence, confidence)


def _max_confidence(a: Optional[str], b: Optional[str]) -> Optional[str]:
    rank = {"low": 1, "medium": 2, "high": 3}
    if a not in rank:
        return b
    if b not in rank:
        return a
    return a if rank[a] >= rank[b] else b


def _extract_numeric_like_tokens(text: str) -> List[str]:
    if not text:
        return []

    return NUMERIC_LIKE_TOKEN_RE.findall(text)


def _infer_raw_triplet_tokens(tokens: List[str]) -> Dict[str, Optional[str]]:
    """
    normalized line에서 뒤쪽 숫자 토큰들로 raw triplet 후보를 잡는다.

    우선순위:
    - 3개 이상이면 마지막 3개를 unit / qty / price 후보로 사용
    - 2개면 unit / price만 사용
    """
    if not tokens:
        return {
            "unit_price_raw": None,
            "qty_raw": None,
            "price_raw": None,
        }

    if len(tokens) >= 3:
        last3 = tokens[-3:]
        return {
            "unit_price_raw": last3[0],
            "qty_raw": last3[1],
            "price_raw": last3[2],
        }

    if len(tokens) == 2:
        return {
            "unit_price_raw": tokens[0],
            "qty_raw": None,
            "price_raw": tokens[1],
        }

    return {
        "unit_price_raw": None,
        "qty_raw": None,
        "price_raw": tokens[-1],
    }


def _qty_raw_supports_expected(
    *,
    qty_raw: Optional[str],
    expected_qty: int,
) -> bool:
    """
    qty OCR sticky noise 보정 지원 여부

    예:
    - qty_raw="21", expected_qty=2 -> True
    - qty_raw="2|", expected_qty=2 -> True
    - qty_raw="2I", expected_qty=2 -> True
    - qty_raw="2 1", expected_qty=2 -> True
    """
    if qty_raw is None:
        return False

    raw = str(qty_raw).strip()
    if not raw:
        return False

    expected_str = str(expected_qty)

    # 완전 정규 숫자만 같으면 복구 대상 아님
    raw_digits_only = re.sub(r"\D", "", raw)
    if raw_digits_only == expected_str:
        return False

    compact = raw.replace(",", "")
    compact = compact.replace("x", "").replace("X", "")

    # 1) expected가 prefix이고 나머지가 sticky noise 또는 흔한 OCR 꼬리면 허용
    if compact.startswith(expected_str):
        tail = compact[len(expected_str):]
        if tail and all(ch in NOISE_CHARS_IN_QTY or ch == "1" for ch in tail):
            return True

    # 2) 숫자만 뽑았을 때 expected가 앞자리이고 나머지 꼬리가 '1'뿐인 경우 허용
    if raw_digits_only.startswith(expected_str):
        tail_digits = raw_digits_only[len(expected_str):]
        if tail_digits and set(tail_digits) == {"1"}:
            return True

    # 3) 공백/노이즈 제거 후 expected 자체가 포함되는데 나머지가 노이즈일 때
    cleaned = "".join(ch for ch in compact if ch not in NOISE_CHARS_IN_QTY)
    if cleaned.startswith(expected_str):
        tail = cleaned[len(expected_str):]
        if tail and set(tail) == {"1"}:
            return True

    return False


def _numeric_raw_supports_expected(
    *,
    raw_token: Optional[str],
    expected_value: int,
) -> bool:
    """
    unit_price raw가 expected 숫자 패턴을 포함하는지 보수적으로 판단

    예:
    - raw="100 %1,590", expected=1590 -> True
    """
    if raw_token is None:
        return False

    raw = str(raw_token).strip()
    if not raw:
        return False

    expected_digits = str(abs(expected_value))
    raw_digits = _digits_only(raw)

    if raw_digits == expected_digits:
        return False

    # raw 안에 expected_digits가 그대로 포함
    if expected_digits in raw_digits:
        return True

    # 공백/노이즈 제거 후 포함
    compact = "".join(ch for ch in raw if ch not in NOISE_CHARS_IN_NUMERIC)
    compact_digits = _digits_only(compact)
    if expected_digits in compact_digits:
        return True

    return False


def _price_raw_supports_expected(
    *,
    raw_token: Optional[str],
    expected_value: int,
) -> bool:
    """
    price noisy correction은 매우 보수적으로 판단한다.

    허용 예시:
    - raw_token이 None/빈값이 아니고
    - digits 차이가 1자리 이하이며
    - expected digits가 raw digits를 포함하거나 그 반대
    """
    if raw_token is None:
        return False

    raw = str(raw_token).strip()
    if not raw:
        return False

    expected_digits = str(abs(expected_value))
    raw_digits = _digits_only(raw)

    if not raw_digits or raw_digits == expected_digits:
        return False

    if abs(len(expected_digits) - len(raw_digits)) > 1:
        return False

    if expected_digits in raw_digits or raw_digits in expected_digits:
        return True

    return False


def _is_confusable_single_digit_substitution(a: int, b: int) -> bool:
    """
    두 숫자가 자리수 동일 + 정확히 1자리만 다르고,
    그 차이가 OCR 혼동쌍일 때만 True

    예:
    - 18790 vs 13790 -> True  (8 <-> 3)
    - 19000 vs 10000 -> False (9 <-> 0 은 현재 허용 안 함)
    """
    sa = str(abs(a))
    sb = str(abs(b))

    if len(sa) != len(sb):
        return False

    diff_pairs = [(x, y) for x, y in zip(sa, sb) if x != y]

    if len(diff_pairs) != 1:
        return False

    return diff_pairs[0] in CONFUSABLE_DIGIT_PAIRS


def _digits_only(text: str) -> str:
    return re.sub(r"\D", "", str(text or ""))


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None
