from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional

from receipt_parser.normalizer import (
    cast_amount_token,
    cast_discount_amount,
    cast_qty_token,
    cleanup_name_candidate,
)


def extract_fields(
    line_text: str,
    normalized_line_text: str,
    line_type: str,
    store: str,
    store_rules: Any,
) -> Dict[str, Any]:
    """
    line_type이 정해진 뒤, 필요한 필드만 추출한다.

    반환 필드:
    - code
    - qty
    - unit_price_raw
    - price_raw
    - discount_raw
    - name_raw
    - subtotal_count

    필드 의미 정리:
    - item_detail
      - unit_price_raw: 상품 단가 후보
      - price_raw: 상품 라인 총액 후보
      - discount_raw: 사용하지 않음 (None)

    - discount_detail
      - unit_price_raw: 할인 라인 내부 단가 후보
      - price_raw: 할인 라인 내부 총액 후보
      - discount_raw: 실제 할인액으로 우선 사용하는 필드
        (semantic 단계에서는 discount_raw를 우선 사용)
      - qty=1인 할인 라인은 unit_price_raw / price_raw / discount_raw가
        동일한 값으로 보일 수 있음. 이는 공통 스키마 유지에 따른 정상 동작이다.

    - receipt_discount
      - discount_raw: 영수증 전역 할인 금액
      - price_raw: 원문 총액 보존용으로 동일 금액 저장 가능
      - name_raw: 할인 라벨명

    - fee
      - price_raw: 별도 금액 항목
      - name_raw: 항목명 (예: 공 병)

    - subtotal / total
      - price_raw: 집계 금액 후보
      - subtotal_count: subtotal 라인의 상품 개수 후보

    - item_name / discount_target
      - name_raw: 원문 기반 이름 후보
    """
    base = _empty_fields()

    raw = (line_text or "").strip()
    text = (normalized_line_text or "").strip()
    store = (store or "").lower()

    if not text:
        return base

    if line_type == "item_detail":
        parsed = _parse_detail_line(
            text=text,
            patterns=store_rules.get("item_patterns", []),
            is_discount=False,
        )
        base.update(parsed)

        # emart 통합형 한 줄 item_detail이면 이름도 함께 복원
        if (
            store == "emart"
            and not base.get("name_raw")
            and not re.match(r"^\*?\d{13}\s", raw.strip())
        ):
            inline_name = _extract_inline_item_name_for_emart(raw)
            if inline_name:
                base["name_raw"] = cleanup_name_candidate(
                    text=inline_name,
                    store=store,
                    store_rules=store_rules,
        )

        return base

    if line_type == "discount_detail":
        parsed = _parse_detail_line(
            text=text,
            patterns=store_rules.get("discount_patterns", []),
            is_discount=True,
        )
        base.update(parsed)

        # emart 프로모션명 + 할인금액 구조에서는 이름을 같이 들고 가도 됨
        if store == "emart" and not base.get("name_raw"):
            discount_name = _extract_discount_name(raw)
            if discount_name:
                base["name_raw"] = cleanup_name_candidate(
                    text=discount_name,
                    store=store,
                    store_rules=store_rules,
                )

        return base

    if line_type == "receipt_discount":
        base.update(_parse_receipt_discount_line(raw, text, store, store_rules))
        return base

    if line_type == "fee":
        base.update(_parse_fee_line(raw, text, store, store_rules))
        return base

    if line_type == "subtotal":
        subtotal_count = _extract_subtotal_count(text)
        last_amount = _extract_last_amount(text)

        base["subtotal_count"] = subtotal_count

        # count-only subtotal 예:
        # "상품수 소계 : 10"
        # -> 이 경우 price_raw까지 10으로 넣지 않음
        if last_amount is not None and last_amount != subtotal_count:
            base["price_raw"] = last_amount

        return base

    if line_type == "total":
        base["price_raw"] = _extract_last_amount(text)
        return base

    if line_type in {"item_name", "discount_target"}:
        base["name_raw"] = cleanup_name_candidate(
            text=raw,
            store=store,
            store_rules=store_rules,
        )
        return base

    if line_type == "discount_keyword":
        # CPN 같은 키워드 라인은 필드 추출 없음
        return base

    if line_type == "noise":
        return base

    return base


# =========================================================
# Internal helpers
# =========================================================

def _empty_fields() -> Dict[str, Any]:
    return {
        "code": None,
        "qty": None,
        "unit_price_raw": None,
        "price_raw": None,
        "discount_raw": None,
        "name_raw": None,
        "subtotal_count": None,
        "is_restored": False,
        "restore_reason": None,
        "restored_fields": [],
    }


def _parse_detail_line(
    text: str,
    patterns: Iterable[re.Pattern],
    is_discount: bool,
) -> Dict[str, Any]:
    """
    item_detail / discount_detail 패턴 매칭 후 필드 추출

    공통 스키마를 유지하기 위해 item_detail과 discount_detail 모두
    unit_price_raw / price_raw를 채운다.

    해석 기준:
    - item_detail:
      - unit_price_raw = 상품 단가
      - price_raw = 상품 총액

    - discount_detail:
      - unit_price_raw = 할인 라인 내부 단가 후보
      - price_raw = 할인 라인 내부 총액 후보
      - discount_raw = 실제 할인액으로 사용할 정규화 필드

    주의:
    - discount_detail에서 qty=1이면
      unit_price_raw == price_raw == discount_raw 로 보일 수 있다.
    - 이 경우에도 semantic 단계에서는 discount_raw를 우선 사용한다.
    - price_raw는 원문 총액 보존용 성격이 강하다.
    """
    candidate_texts = [text]

    # item_detail에서만 숫자 찢김 복원 후보 추가
    if not is_discount:
        repaired_text = _repair_split_item_detail_numbers(text)
        if repaired_text and repaired_text != text:
            candidate_texts.append(repaired_text)

    for candidate_text in candidate_texts:
        for pattern in patterns:
            m = pattern.match(candidate_text)
            if not m:
                continue

            gd = m.groupdict()

            code = gd.get("code")
            qty = cast_qty_token(gd.get("qty"))
            unit_price_raw = cast_amount_token(gd.get("unit_price"))
            price_raw = cast_amount_token(gd.get("price"))

            restored_fields = []
            restore_reason = None

            # 숫자 찢김 복원으로 pattern match된 경우 태깅
            if candidate_text != text:
                restored_fields.append("line_text_numeric_repaired")
                restore_reason = "split numeric tokens merged before pattern match"

            # code 앞 * 제거
            if isinstance(code, str):
                code = code.lstrip("*")

            # 1) qty 기본 보정
            if qty is None:
                inferred_qty = _infer_qty_as_one_when_missing(
                    unit_price_raw=unit_price_raw,
                    price_raw=price_raw,
                )
                if inferred_qty is not None:
                    qty = inferred_qty
                    restored_fields.append("qty")
                    if restore_reason is None:
                        restore_reason = "unit_price == price -> qty=1"

            # 2) 2-of-3 복원
            if code or unit_price_raw is not None or price_raw is not None:
                present_count = sum(
                    v is not None for v in [qty, unit_price_raw, price_raw]
                )

                if present_count == 2:
                    # qty + unit_price -> price
                    if qty is not None and unit_price_raw is not None and price_raw is None:
                        price_raw = qty * unit_price_raw
                        restored_fields.append("price_raw")
                        if restore_reason is None:
                            restore_reason = "price_raw inferred from qty * unit_price"

                    # qty + price -> unit_price
                    elif qty is not None and price_raw is not None and unit_price_raw is None:
                        if qty != 0 and price_raw % qty == 0:
                            unit_price_raw = price_raw // qty
                            restored_fields.append("unit_price_raw")
                            if restore_reason is None:
                                restore_reason = "unit_price inferred from price_raw / qty"

                    # unit_price + price -> qty
                    elif unit_price_raw is not None and price_raw is not None and qty is None:
                        if unit_price_raw != 0 and price_raw % unit_price_raw == 0:
                            qty = price_raw // unit_price_raw
                            restored_fields.append("qty")
                            if restore_reason is None:
                                restore_reason = "qty inferred from price_raw / unit_price"

            result = {
                "code": code,
                "qty": qty,
                "unit_price_raw": abs(unit_price_raw) if isinstance(unit_price_raw, int) else None,
                "price_raw": abs(price_raw) if isinstance(price_raw, int) else None,
                "discount_raw": None,
                "name_raw": None,
                "subtotal_count": None,
                "is_restored": False,
                "restore_reason": None,
                "restored_fields": [],
            }

            # price mismatch correction (OCR 깨짐 대응)
            if (
                not is_discount
                and result.get("qty")
                and result.get("unit_price_raw")
                and result.get("price_raw")
            ):
                expected = result["qty"] * result["unit_price_raw"]

                if result["price_raw"] != expected:
                    result["price_raw"] = expected

                    if "price_raw" not in restored_fields:
                        restored_fields.append("price_raw")

                    result["is_restored"] = True
                    if result["restore_reason"] is None:
                        result["restore_reason"] = "price_raw corrected from unit_price * qty"
                    result["restored_fields"] = restored_fields

            if is_discount:
                result["discount_raw"] = cast_discount_amount(gd.get("price"))
                if result["discount_raw"] is None and result["price_raw"] is not None:
                    result["discount_raw"] = result["price_raw"]

            if restored_fields:
                result["is_restored"] = True
                if result["restore_reason"] is None:
                    result["restore_reason"] = restore_reason
                result["restored_fields"] = restored_fields

            return result

    return _empty_fields()


def _parse_receipt_discount_line(
    raw: str,
    text: str,
    store: str,
    store_rules: Any,
) -> Dict[str, Any]:
    """
    receipt-level discount 추출

    예:
    - 15%할인 : 2201606094 - 3,000
    - 결제할인 : 2201606006 -4,410
    - [앱]룰렛3천원 : 2201606243 -3,000
    - 삼성카드할인 : 2211101938 -5,000
    """
    base = _empty_fields()

    discount_amount = _extract_last_discount_amount(text)
    if discount_amount is not None:
        base["discount_raw"] = discount_amount
        base["price_raw"] = discount_amount

    # 코드 추출
    m_code = re.search(r":\s*(\d+)\s*-\s*[\d,]+$", text)
    if m_code:
        base["code"] = m_code.group(1)

    # 이름 추출
    name = raw
    if ":" in raw:
        name = raw.split(":", 1)[0].strip()

    cleaned_name = cleanup_name_candidate(
        text=name,
        store=store,
        store_rules=store_rules,
    )
    base["name_raw"] = cleaned_name or name

    return base


def _parse_fee_line(
    raw: str,
    text: str,
    store: str,
    store_rules: Any,
) -> Dict[str, Any]:
    """
    fee line 추출

    예:
    - 공 병 600
    """
    base = _empty_fields()

    amount = _extract_last_amount(text)
    if amount is not None:
        base["price_raw"] = amount
        base["unit_price_raw"] = amount
        base["qty"] = 1

    name = raw
    m = re.match(r"^(.*?)([+-]?\d[\d,]*)$", raw.strip())
    if m:
        candidate_name = m.group(1).strip()
        if candidate_name:
            name = candidate_name

    cleaned_name = cleanup_name_candidate(
        text=name,
        store=store,
        store_rules=store_rules,
    )
    base["name_raw"] = cleaned_name or name

    return base


def _infer_qty_as_one_when_missing(
    unit_price_raw: Optional[int],
    price_raw: Optional[int],
) -> Optional[int]:
    """
    최소 규칙:
    qty 그룹이 없는데 unit_price == price 이면 qty=1로 본다.
    """
    if unit_price_raw is None or price_raw is None:
        return None

    if abs(unit_price_raw) == abs(price_raw):
        return 1

    return None


def _extract_subtotal_count(text: str) -> Optional[int]:
    """
    subtotal 라인에서 상품 개수 추출

    예:
    - 상품수 소계 : 10
    - (Sub-총상품수 : 13) 144420
    - (Sub-총상품 : 5)
    - (Sub-총싱품수 : 6) 80510

    규칙:
    1) subtotal 관련 키워드 뒤의 첫 숫자를 우선 count로 본다.
    2) 마지막 금액(price_raw)과 혼동하지 않도록 '마지막 숫자'가 아니라
       키워드 근처 숫자를 잡는다.
    """
    if not text:
        return None

    compact = re.sub(r"\s+", "", text)

    patterns = [
        r"(?:상품수소계|총상품수|총싱품수|총상품)\D*(\d+)",
        r"(?:Sub[-_]?(?:총상품수|총싱품수|총상품))\D*(\d+)",
    ]

    for pattern in patterns:
        m = re.search(pattern, compact, flags=re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except (TypeError, ValueError):
                return None

    return None


def _extract_last_amount(text: str) -> Optional[int]:
    """
    subtotal / total / fee 라인에서 마지막 금액 추출

    예:
    - 상품수 소계 : 10
    - 합계 (VAT 포함) 232,330
    - (Sub-총상품수 : 13) 144420
    - 공 병 600

    반환값은 subtotal / total / fee 계열에서 price_raw로 사용된다.
    """
    candidates = re.findall(r"[+-]?\d[\d,]*-?[Tt]?", text)
    if not candidates:
        return None

    return cast_amount_token(candidates[-1])


def _extract_last_discount_amount(text: str) -> Optional[int]:
    """
    할인 계열 라인에서 마지막 음수 금액 추출

    예:
    - 컵밥류 2+1 -1,660
    - 결제할인 : 2201606006 -4,410
    - [앱]룰렛3천원 : 2201606243 -3,000
    """
    m = re.search(r"-\s*([\d,]+)\s*$", text)
    if m:
        return cast_discount_amount(m.group(1))

    candidates = re.findall(r"[+-]?\d[\d,]*-?[Tt]?", text)
    if not candidates:
        return None

    return cast_discount_amount(candidates[-1])


def _extract_discount_name(raw: str) -> Optional[str]:
    """
    discount_detail에서 할인명 추출

    예:
    - 컵밥류 2+1 -1,660 -> 컵밥류 2+1
    - 포인트카드 -15,000 -> 포인트카드
    """
    if not raw:
        return None

    m = re.match(r"^(.*?)\s*-\s*[\d,]+\s*$", raw.strip())
    if m:
        name = m.group(1).strip()
        return name or None

    return None


def _extract_inline_item_name_for_emart(raw: str) -> Optional[str]:
    """
    emart 통합형 item_detail에서 이름 부분 복원

    허용 예:
    - "* 01 (Ph)돌바나나(송이) 2,280 1 2,280"
    - "퍼실 딥클린 파워젤 26,980 3 80,940"

    비허용 예:
    - "8801121027097 1,450 1 1,450"
    - "*8801013770025 280 4 1,120"
    - "1500000018153 5,480 5,480"
    """
    if not raw:
        return None

    text = raw.strip()

    # ---------------------------------------------------------
    # 1) 바코드형 detail은 이름 복원 금지
    # ---------------------------------------------------------
    if re.match(r"^\*?\d{13}\s+[\d,]+(?:\s+\d+)?\s+[\d,]+\s*$", text):
        return None

    # ---------------------------------------------------------
    # 2) 통합형: 뒤쪽 숫자 3토큰 제거
    #    ex) 상품명 26,980 3 80,940
    # ---------------------------------------------------------
    m = re.match(r"^(.*?)\s+[\d,]+\s+\d+\s+[\d,]+\s*$", text)
    if not m:
        return None

    name = m.group(1).strip()

    # 선행 *, 번호 제거
    name = re.sub(r"^\*\s*", "", name)
    name = re.sub(r"^\d{2,3}\*?\s+", "", name)
    name = re.sub(r"^\*\s*\d{2,3}\s+", "", name)

    return name or None



def _repair_split_item_detail_numbers(text: str) -> str:
    """
    item_detail 숫자 찢김 보정

    현재는 아주 제한적인 케이스만 보정한다.

    예:
    - "612001 1 9790 0 580"
      -> "612001 1 9790 9790"

    이유:
    - qty=1이고 unit_price가 명확한데,
      뒤의 "0 580"은 price 토큰이 빛번짐/OCR 오류로 찢어진 경우로 본다.
    - 이 경우 기존처럼 "580"만 price로 쓰면 오복원이 되므로,
      qty=1이면 price를 unit_price와 동일하게 복원한다.

    목표:
    - pattern match 전에 최소한의 숫자 구조 복원만 수행
    - 과한 추론은 하지 않음
    """
    if not text:
        return text

    tokens = text.split()
    if len(tokens) < 5:
        return text

    # code qty unit_price 0 xxx  -> code qty unit_price unit_price
    if (
        len(tokens) == 5
        and re.fullmatch(r"\d{4,7}", tokens[0] or "")
        and re.fullmatch(r"1[xX]?", tokens[1] or "")
        and re.fullmatch(r"[\d,]+", tokens[2] or "")
        and tokens[3] == "0"
        and re.fullmatch(r"\d{3}", tokens[4] or "")
    ):
        return " ".join([tokens[0], tokens[1], tokens[2], tokens[2]])

    return text