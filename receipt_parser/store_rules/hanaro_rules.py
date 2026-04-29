from __future__ import annotations

import re
from typing import Any, Dict


# =========================================================
# ITEM DETAIL PATTERNS
# =========================================================
# 대응 케이스:
# *265405 17,690 1 17,690
# 8801045447001 2,180 1 2,180
# * 8809636710008 7,890 1 7,890
# 001*8801448212053 1,680 1 1,680
# 002*2100051133899 2,000 2 4.000
# 003*253211 12.900 1 12.900
# *230438 2,700 2,700                 (qty 없음 -> 1)
# =========================================================

_AMOUNT = r"-?[\d,.]+"

ITEM_PATTERNS = [
    # item no + * + code + unit_price + qty + price
    # ex) 001*8801448212053 1,680 1 1,680
    re.compile(
        rf"^\d{{3}}\*"
        rf"(?P<code>\d{{6,13}})\s+"
        rf"(?P<unit_price>{_AMOUNT})\s+"
        rf"(?P<qty>\d+)\s+"
        rf"(?P<price>{_AMOUNT})$"
    ),

    # item no + space + * + code + unit_price + qty + price
    # ex) 001 * 8801448212053 1,680 1 1,680
    re.compile(
        rf"^\d{{3}}\s+\*\s*"
        rf"(?P<code>\d{{6,13}})\s+"
        rf"(?P<unit_price>{_AMOUNT})\s+"
        rf"(?P<qty>\d+)\s+"
        rf"(?P<price>{_AMOUNT})$"
    ),

    # optional * + code + unit_price + qty + price
    # ex) *265405 17,690 1 17,690
    # ex) 8801045352107 3,060 1 3,060
    re.compile(
        rf"^\*?\s*"
        rf"(?P<code>\d{{6,13}})\s+"
        rf"(?P<unit_price>{_AMOUNT})\s+"
        rf"(?P<qty>\d+)\s+"
        rf"(?P<price>{_AMOUNT})$"
    ),

    # optional * + code + unit_price + price
    # qty 없음 -> extractor에서 qty=1 보정
    # ex) *230438 2,700 2,700
    re.compile(
        rf"^\*?\s*"
        rf"(?P<code>\d{{6,13}})\s+"
        rf"(?P<unit_price>{_AMOUNT})\s+"
        rf"(?P<price>{_AMOUNT})$"
    ),
]


# =========================================================
# DISCOUNT DETAIL PATTERNS
# =========================================================
# 대응 케이스:
# 삼겹 한돈자조금 할인 -1.369
# 005c99260200119192 -2.730 1 -2.730
# c8806163190310 -660 1 -660
# c9900015039990 -5,000 1 -5.000
# =========================================================

DISCOUNT_PATTERNS = [
    # code/prefix + negative_unit_price + qty + negative_price
    # 반드시 음수 금액이어야 discount_detail로 인정
    # 예:
    # c8806163190310 -660 1 -660
    # c9900015039990 -5,000 1 -5.000
    # 005c99260200119192 -2.730 1 -2.730
    re.compile(
        rf"^(?P<code>\d{{3}}?[A-Za-z]?\d{{6,20}}|[A-Za-z]?\d{{6,20}})\s+"
        rf"(?P<unit_price>-[\d,.]+)\s+"
        rf"(?P<qty>\d+)\s+"
        rf"(?P<price>-[\d,.]+)$"
    ),

    # promotion/name + negative amount
    re.compile(
        rf"^.+?\s*-\s*(?P<price>[\d,.]+)$"
    ),
]


# =========================================================
# RECEIPT DISCOUNT PATTERNS
# =========================================================
# 대응 케이스:
# 끝전할인: -4
# 끝 전할 인: -1
# 총할인액: -4
# 쿠폰할인: -660
# 농축산물 할인쿠폰 (4월2차) -1,400
# =========================================================

RECEIPT_DISCOUNT_PATTERNS = [
    # label : -amount
    re.compile(
        rf"^(?P<name>.+?)\s*:\s*-\s*(?P<price>[\d,.]+)$"
    ),

    # 끝 전할 인 OCR 분절
    re.compile(
        rf"^(?P<name>끝\s*전\s*할\s*인)\s*:?\s*-\s*(?P<price>[\d,.]+)$"
    ),

    # label -amount
    re.compile(
        rf"^(?P<name>.+?(?:할인|할인쿠폰|총할인액))\s*-\s*(?P<price>[\d,.]+)$"
    ),
]


# =========================================================
# KEYWORDS
# =========================================================

DISCOUNT_KEYWORDS = set()

DISCOUNT_TARGET_SUFFIX = set()
DISCOUNT_TARGET_PREFIX = set()


# =========================================================
# SUMMARY / TOTAL
# =========================================================

SUBTOTAL_KEYWORDS = {
    "총구매액",
}

TOTAL_KEYWORDS = {
    "내실금액",
}


# =========================================================
# RECEIPT DISCOUNT
# =========================================================

RECEIPT_DISCOUNT_KEYWORDS = {
    "끝전할인",
    "끝 전할 인",
    "총할인액",
    "쿠폰할인",
    "할인쿠폰",
    "농축산물 할인쿠폰",
}

BODY_DISCOUNT_HINT_KEYWORDS = {
    "한돈자조금 할인",
    "한돈자조금",
}


# =========================================================
# TAX / INFO
# =========================================================

TAX_KEYWORDS = {
    "면세",
    "과세",
    "부가세",
}


# =========================================================
# NOISE
# =========================================================

NOISE_KEYWORDS = {
    "상품(코드) 단가 수량 금액",
    "상품코드 단가 수량 금액",
    "상품명 단가 수량 금액",
    "단가 수량 금액",
    "이벤트 할인",
}

NOISE_PATTERNS = [
    # [3,800] 같은 상품명 보조 가격 표기 단독 라인
    re.compile(r"^\[\s*[\d,.]+\s*\]$"),
]


# =========================================================
# NAME CLEANUP
# cleanup_name_candidate에서 활용
# =========================================================

NAME_CLEANUP_PATTERNS = [
    # 001 P삼겹살 / 007 P뒷다리...
    re.compile(r"^\d{3}\s+"),

    # 006 [카드쿠폰(율)]선진 삼겹
    re.compile(r"^\d{3}\s*"),

    # COB P커피땅콩...
    re.compile(r"^[A-Za-z]{2,4}\s+"),

    # 상품명 안의 [3,800], [카드쿠폰(율)] 같은 보조 태그 제거
    re.compile(r"\[[^\]]+\]"),

    # leading *
    re.compile(r"^\*\s*"),
]


# =========================================================
# RULE OBJECT
# =========================================================

HANARO_RULES: Dict[str, Any] = {
    "store": "hanaro",

    # patterns
    "item_patterns": ITEM_PATTERNS,
    "discount_patterns": DISCOUNT_PATTERNS,
    "receipt_discount_patterns": RECEIPT_DISCOUNT_PATTERNS,
    "fee_patterns": [],
    "noise_patterns": NOISE_PATTERNS,

    # keywords
    "discount_keywords": DISCOUNT_KEYWORDS,
    "discount_target_suffix": DISCOUNT_TARGET_SUFFIX,
    "discount_target_prefix": DISCOUNT_TARGET_PREFIX,

    "body_discount_hint_keywords": BODY_DISCOUNT_HINT_KEYWORDS,
    "subtotal_keywords": SUBTOTAL_KEYWORDS,
    "total_keywords": TOTAL_KEYWORDS,
    "receipt_qty_keywords": set(),
    "receipt_discount_keywords": RECEIPT_DISCOUNT_KEYWORDS,
    "tax_keywords": TAX_KEYWORDS,
    "noise_keywords": NOISE_KEYWORDS,

    # cleanup
    "name_cleanup_patterns": NAME_CLEANUP_PATTERNS,

    # hints
    "item_detail_hints": {
        "qty_missing_default": 1,
        "allow_star_prefix": True,
        "allow_item_no_prefix": True,
        "allow_dot_amount_separator": True,
        "code_min_len": 6,
        "code_max_len": 13,
    },
    "discount_detail_hints": {
        "extract_last_negative_amount": True,
        "attach_to_previous_item": True,
        "allow_dot_amount_separator": True,
    },
    "receipt_discount_hints": {
        "dedupe_same_amount": True,
        "summary_discount_keyword": "총할인액",
    },
}


def get_hanaro_rules() -> Dict[str, Any]:
    return HANARO_RULES