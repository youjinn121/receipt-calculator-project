from __future__ import annotations

import re
from typing import Any, Dict


# =========================================================
# ITEM DETAIL PATTERNS (named group 기반)
# =========================================================
# 대응 케이스:
# 8801121027097 1,450 1 1,450
# *8801013770025 280 4 1,120
# 1500000018153 5,480 5,480          (qty 없음 -> 1)
# *8809205164010 4,820 4,820          (qty 없음 -> 1)
# * 01 (Ph)돌바나나(송이) 2,280 1 2,280
# 퍼실 딥클린 파워젤 26,980 3 80,940
#
# 주의:
# - 통합형 item_detail에서는 extractor가 숫자 필드만 뽑고
#   이름은 별도 helper(_extract_inline_item_name_for_emart)로 복원함
# - 따라서 여기서는 name group이 없어도 됨
# =========================================================

ITEM_PATTERNS = [
    # 13자리 바코드 + 단가 + 수량 + 금액
    re.compile(
        r"^(?P<code>\*?\d{13})\s+"
        r"(?P<unit_price>[\d,]+)\s+"
        r"(?P<qty>\d+)\s+"
        r"(?P<price>[\d,]+)$"
    ),

    # 13자리 바코드 + 단가 + 금액 (qty 없음 -> extractor에서 1 보정)
    re.compile(
        r"^(?P<code>\*?\d{13})\s+"
        r"(?P<unit_price>[\d,]+)\s+"
        r"(?P<price>[\d,]+)$"
    ),

    # "* 01 (Ph)돌바나나(송이) 2,280 1 2,280"
    # code는 없음, inline 통합형
    re.compile(
        r"^\*\s*\d{2,3}\s+.+\s+"
        r"(?P<unit_price>[\d,]+)\s+"
        r"(?P<qty>\d+)\s+"
        r"(?P<price>[\d,]+)$"
    ),

    # "퍼실 딥클린 파워젤 26,980 3 80,940"
    # code는 없음, inline 통합형
    re.compile(
        r"^.+\s+"
        r"(?P<unit_price>[\d,]+)\s+"
        r"(?P<qty>\d+)\s+"
        r"(?P<price>[\d,]+)$"
    ),
]


# =========================================================
# DISCOUNT DETAIL PATTERNS (named group 기반)
# =========================================================
# 대응 케이스:
# 컵밥류 2+1 -1,660
# 샌드류5개5천 -5,000
# [앱]고소미50% -1,400
# 포인트카드 -15,000
# [잡화/반려] 24년 1주 -1,500
# 프로모션명 1+1 -4,000 / 프로모션명 2+1 -1,480
#
# 주의:
# - 이마트 discount_detail은 대부분 code/qty/unit_price가 없음
# - extractor가 discount_raw를 만들려면 최소한 price named group은 필요
# - name_raw는 extractor의 _extract_discount_name()에서 raw 기준으로 보조 추출
# =========================================================

DISCOUNT_PATTERNS = [
    # 일반형: "프로모션명 ... -1,660"
    re.compile(
        r"^.+?\s*-\s*(?P<price>[\d,]+)$"
    ),

    # 다중 프로모션형:
    # "프로모션명 1+1 -4,000 / 프로모션명 2+1 -1,480"
    # 마지막 할인금액만 추출
    re.compile(
        r"^.+/\s*.+?\s*-\s*(?P<price>[\d,]+)$"
    ),
]


# =========================================================
# RECEIPT DISCOUNT PATTERNS
# =========================================================
# 대응 케이스:
# 15%할인 : 2201606094 - 3,000
# 결제할인 : 2201606006 -4,410
# [앱]룰렛3천원 : 2201606243 -3,000
# 삼성카드할인 : 2211101938 -5,000
#
# 주의:
# - 현재 line_classifier helper는 match 여부만 주로 쓰지만
#   extractor/후속 확장 대비로 named group도 같이 둠
# =========================================================

RECEIPT_DISCOUNT_PATTERNS = [
    re.compile(
        r"^(?P<name>.+?)\s*:\s*(?P<code>\d+)\s*-\s*(?P<price>[\d,]+)$"
    ),
]


# =========================================================
# FEE PATTERNS
# =========================================================
# 현재 이마트에서는 공병/공 병 라인을 fee로 유지하지 않고
# noise로 처리한다.
# 이유:
# - item 정산에 사용하지 않음
# - receipt total 검증에도 직접 쓰지 않음
# - 오히려 payment_total_mismatch를 유발할 수 있음
# =========================================================

FEE_PATTERNS = []


# =========================================================
# KEYWORDS
# =========================================================

# 이마트는 [앱]이 단독 keyword 라인으로도 올 수 있지만,
# 현재 classifier의 discount_keyword 판정이 "포함" 기준까지 허용하므로
# [앱]고소미50% -1,400 같은 discount_detail을 오분류할 수 있다.
# 따라서 emart에서는 discount_keyword를 비워두고
# discount_detail / receipt_discount 패턴으로 처리한다.
DISCOUNT_KEYWORDS = set()

# 이마트는 Costco처럼 IRC / EXM / PP target 구조가 없으므로 비움
DISCOUNT_TARGET_SUFFIX = set()
DISCOUNT_TARGET_PREFIX = set()


# =========================================================
# SUMMARY / TOTAL
# =========================================================

SUBTOTAL_KEYWORDS = set()

TOTAL_KEYWORDS = {
    "결제대상금액",
    "제대상금액",   # OCR 오인식 보정
}


# =========================================================
# RECEIPT QTY
# =========================================================
# 영수증 전체 상품 수량 라인
# 예:
# - 총 품목 수량 15
# - 총상품수량 15
# - 총수량 15
#
# 주의:
# - total 금액 라인이 아님
# - noise로 버리지 않고 별도 line_type(receipt_qty)로 처리해야 함
# =========================================================

RECEIPT_QTY_KEYWORDS = {
    "총 품목 수량",
    "총상품수량",
    "총수량",
}

# =========================================================
# RECEIPT DISCOUNT
# =========================================================
# 영수증 전역 할인 키워드
#
# 사용 목적:
# - 합계 이후 ~ 결제대상금액 이전/주변에 등장하는 할인 라인을
#   receipt_discount로 분류하기 위한 키워드
#
# 예:
# - 결제할인 : -5,000
# - 카드할인 : -4,000
# - 삼성카드할인 : 2211101938 -5,000
# - 청구할인 : -3,000
#
# 주의:
# - 상품 바로 아래 단독 음수(-6,500)는 item-level discount_detail로 처리
# - receipt-level 할인은 semantic에서 item에 붙이지 않고
#   tail_info.receipt_discounts / summary.receipt_discount_total로 집계
# =========================================================
RECEIPT_DISCOUNT_KEYWORDS = {
    "결제할인",
    "카드할인",
    "삼성카드할인",
    "청구할인",
    "포인트할인",
}

BODY_DISCOUNT_HINT_KEYWORDS = {
    "에누리",
    "행사",
    "S-POINT",
    "포인트에누리",
    "포인트에누리행사",
    "가공에누리",
}


# =========================================================
# TAX / INFO
# =========================================================

TAX_KEYWORDS = {
    "면세 물품",
    "과세 물품",
    "부 가 세",
    "부가세",
}


# =========================================================
# NOISE
# =========================================================

NOISE_KEYWORDS = {
    "상품명 단 가 수량 금 액",
    "상품코드 단 가 수량 금 액",
    "단 가 수량 금 액",
    "(*)면세 물품",
    "(*) 면세 물품",
    "과세 물품",
    "부 가 세",
    "부가세 면세 물품가액",
    "합 계",
    "공 병",
    "공병",
}

NOISE_PATTERNS = [
    # 브라운돈가스 사공훈 104-86-56057
    re.compile(r"^.+\s+\d{3}-\d{2}-\d{5}$"),
]


# =========================================================
# NAME CLEANUP
# cleanup_name_candidate에서 활용 가능
# =========================================================

NAME_CLEANUP_PATTERNS = [
    # 01 떡붕어싸만코 / 001 큐원아이스크림...
    re.compile(r"^\d{2,3}\*?\s+"),

    # * 국내산냉동옛날삼겹살
    re.compile(r"^\*\s*"),

    # (J)무항생제볶음탕용 / (JN)친환경참타리버섯 / (Ph)돌바나나(송이)
    re.compile(r"^\([A-Za-z]{1,3}\)"),
]


# =========================================================
# RULE OBJECT
# =========================================================

EMART_RULES: Dict[str, Any] = {
    "store": "emart",

    # 패턴
    "item_patterns": ITEM_PATTERNS,
    "discount_patterns": DISCOUNT_PATTERNS,
    "receipt_discount_patterns": RECEIPT_DISCOUNT_PATTERNS,
    "fee_patterns": FEE_PATTERNS,
    "noise_patterns": NOISE_PATTERNS,

    # 키워드
    "discount_keywords": DISCOUNT_KEYWORDS,
    "discount_target_suffix": DISCOUNT_TARGET_SUFFIX,
    "discount_target_prefix": DISCOUNT_TARGET_PREFIX,

    "body_discount_hint_keywords": BODY_DISCOUNT_HINT_KEYWORDS,
    "subtotal_keywords": SUBTOTAL_KEYWORDS,
    "total_keywords": TOTAL_KEYWORDS,
    "receipt_qty_keywords": RECEIPT_QTY_KEYWORDS,
    "receipt_discount_keywords": RECEIPT_DISCOUNT_KEYWORDS,
    "tax_keywords": TAX_KEYWORDS,
    "noise_keywords": NOISE_KEYWORDS,

    # 이름 정리
    "name_cleanup_patterns": NAME_CLEANUP_PATTERNS,

    # 보조 힌트
    "item_detail_hints": {
        "barcode_len": 13,
        "qty_missing_default": 1,
        "allow_star_prefix": True,
        "allow_inline_name_detail": True,
    },
    "discount_detail_hints": {
        "extract_last_negative_amount": True,
        "attach_to_previous_item": True,
    },
}


def get_emart_rules() -> Dict[str, Any]:
    return EMART_RULES