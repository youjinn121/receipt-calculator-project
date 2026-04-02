import re


# =========================================================
# ITEM DETAIL PATTERNS (robust)
# =========================================================
# 다양한 케이스 대응:
# 650635 1x 9,590 9,590
# 502305 1 2990 2,990T
# 630218 7990 7,990 T
# 004457 1 2500 2,500-T

ITEM_PATTERNS = [
    # code + qty + unit_price + price (+ optional T)
    re.compile(
        r"^(?P<code>\d{4,7})\s+"
        r"(?P<qty>\d+\s*[xX]?)\s+"
        r"(?P<unit_price>[\d,]+)\s+"
        r"(?P<price>[\d,]+)\s*"
        r"(?:T)?$"
    ),

    # code + unit_price + price (qty 없음 → 1)
    re.compile(
        r"^(?P<code>\d{4,7})\s+"
        r"(?P<unit_price>[\d,]+)\s+"
        r"(?P<price>[\d,]+)\s*"
        r"(?:T)?$"
    ),
]





# =========================================================
# DISCOUNT DETAIL PATTERNS (robust)
# =========================================================
# 대응 케이스:
# 11816 1x 1,800 1,800-
# 004457 1 2500 2,500-T
# 673859 1x 3,000 3,000-T
# 24164 1x 1,700 1,700-
# (qty 없는 변형 대응)
# 123456 1800 1,800-
# 123456 2500 2,500-T

DISCOUNT_PATTERNS = [
    # code + qty + unit_price + price-
    re.compile(
        r"^(?P<code>\d{4,7})\s+"
        r"(?P<qty>\d+\s*[xX]?)\s+"
        r"(?P<unit_price>[\d,]+)\s+"
        r"(?P<price>[\d,]+)\s*-$"
    ),

    # code + qty + unit_price + price-T / T-
    re.compile(
        r"^(?P<code>\d{4,7})\s+"
        r"(?P<qty>\d+\s*[xX]?)\s+"
        r"(?P<unit_price>[\d,]+)\s+"
        r"(?P<price>[\d,]+)\s*(?:-T|T-)$"
    ),

    # code + unit_price + price- (qty 없음 → 1)
    re.compile(
        r"^(?P<code>\d{4,7})\s+"
        r"(?P<unit_price>[\d,]+)\s+"
        r"(?P<price>[\d,]+)\s*-$"
    ),

    # code + unit_price + price-T / T- (qty 없음 → 1)
    re.compile(
        r"^(?P<code>\d{4,7})\s+"
        r"(?P<unit_price>[\d,]+)\s+"
        r"(?P<price>[\d,]+)\s*(?:-T|T-)$"
    ),
]


# =========================================================
# KEYWORDS
# =========================================================

# 할인 키워드
DISCOUNT_KEYWORDS = {
    "CPN",
    "자사 쿠폰",
    "쿠폰",
    "마스터쿠폰",
}

# 할인 대상 suffix / prefix
DISCOUNT_TARGET_SUFFIX = {
    "IRC",
    "EXM",
    "PP",
}

DISCOUNT_TARGET_PREFIX = {
    "IRC",
    "EXM",
    "PP",
}


# =========================================================
# SUMMARY / TOTAL
# =========================================================

SUBTOTAL_KEYWORDS = {
    "상품수 소계",
    "Sub-총상품수",
    "Sub-총상품",
    "총상품",
    "총상품수",
}

TOTAL_KEYWORDS = {
    "합계",
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
    "판매",
    "BEGIN",
    "END",
    "CHECK",
    "Bottom Of Basket",
    "Item Count",
}


# =========================================================
# RULE OBJECT
# =========================================================

COSTCO_RULES = {
    "store": "costco",

    # 패턴
    "item_patterns": ITEM_PATTERNS,
    "discount_patterns": DISCOUNT_PATTERNS,

    # 키워드
    "discount_keywords": DISCOUNT_KEYWORDS,
    "discount_target_suffix": DISCOUNT_TARGET_SUFFIX,
    "discount_target_prefix": DISCOUNT_TARGET_PREFIX,

    "subtotal_keywords": SUBTOTAL_KEYWORDS,
    "total_keywords": TOTAL_KEYWORDS,
    "tax_keywords": TAX_KEYWORDS,
    "noise_keywords": NOISE_KEYWORDS,
}