"""
[Category Schema]

LLM 기반 카테고리 정규화에서 사용할 고정 카테고리 스키마.

원칙:
- LLM 출력은 반드시 PRIMARY_CATEGORIES 중 하나여야 한다.
- 허용되지 않은 응답은 Uncategorized로 처리한다.
"""

from __future__ import annotations

from typing import List


PRIMARY_CATEGORIES: List[str] = [
    "식재료",
    "간편식",
    "간식",
    "음료",
    "주류",
    "생활용품",
    "반려동물",
    "기타",
    "Uncategorized",
]


CATEGORY_DESCRIPTIONS = {
    "식재료": (
        "채소, 과일, 육류, 수산물, 달걀, 계란, 유정란, 동물복지란, 두부, 우유 등 "
        "조리에 사용되는 기본 재료. "
        "상품명에 '동물복지'가 포함되어도 '란/계란/달걀' 계열이면 식재료로 분류한다."
    ),
    "간편식": "라면, 컵밥, 냉동식품, 즉석식품, 반찬류, 국/탕류, 어묵탕 등 바로 먹거나 간단히 조리하는 식품",
    "간식": "과자, 빵, 초콜릿, 아이스크림, 디저트류",
    "음료": "생수, 탄산음료, 커피, 주스, 차, 우유음료 등 비알코올 음료",
    "주류": "맥주, 소주, 막걸리, 와인 등 알코올 음료",
    "생활용품": "세제, 휴지, 주방용품, 욕실용품, 청소용품 등 비식품 생활 소비재",
    "반려동물": (
        "반려동물 사료, 반려동물 간식, 배변패드, 고양이 모래, 장난감 등 "
        "반려동물 사용 목적이 명확한 상품. "
        "단순히 상품명에 '동물'이 포함된다고 반려동물로 분류하지 않는다."
    ),
    "기타": "의류, 자켓, 신발, 전자제품, 잡화 등 위 카테고리에 명확히 속하지 않는 항목",
    "Uncategorized": "판단 불가, LLM 응답 오류, 허용 카테고리 외 응답",
}


def get_allowed_categories() -> List[str]:
    return list(PRIMARY_CATEGORIES)


def is_allowed_category(category: str) -> bool:
    return category in PRIMARY_CATEGORIES


def normalize_category(category: str) -> str:
    if not category:
        return "Uncategorized"

    cleaned = str(category).strip()

    if cleaned in PRIMARY_CATEGORIES:
        return cleaned

    return "Uncategorized"