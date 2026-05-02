"""
[Fallback Rules]

LLM 호출 전/후에 사용할 간단한 키워드 기반 카테고리 분류 규칙.

역할:
- 명확한 상품은 LLM 없이 즉시 분류
- LLM 실패 시 보조 분류
- 비용 절감 및 안정성 향상

주의:
- 애매한 규칙은 넣지 않는다.
- 확실한 키워드만 사용한다.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from llm.category_schema import normalize_category


CATEGORY_KEYWORDS = {
    "주류": [
        "맥주", "소주", "막걸리", "와인", "청하", "필라이트", "카스", "테라",
        "참이슬", "처음처럼", "국순당", "생막걸리",
    ],
    "간편식": [
        "라면", "탕면", "컵밥", "즉석", "냉동", "만두", "볶음밥", "도시락",
        "햇반", "컵누들", "사발면", "짜파게티", "안성탕면", "신라면",
        "반찬류",
    ],
    "간식": [
        "과자", "스낵", "초콜릿", "초코", "아이스크림", "빵", "쿠키",
        "케이크", "젤리", "사탕", "핫도그", "약과", "디저트", "크라상",
        "크로와상", "버터크라상",
    ],
    "음료": [
        "생수", "탄산", "콜라", "사이다", "주스", "쥬스", "커피", "차",
        "우유음료", "가공유", "두유", "음료",
    ],
    "생활용품": [
        "세제", "휴지", "물티슈", "키친타월", "샴푸", "린스", "비누",
        "치약", "칫솔", "청소", "주방세제", "랩", "호일", "봉투",
    ],
    "반려동물": [
        "강아지", "고양이", "반려", "사료", "배변패드", "펫", "캣", "독",
    ],
    "식재료": [
        "대파", "양파", "마늘", "당근", "부추", "청양", "토마토", "바나나",
        "사과", "배", "귤", "딸기", "수박", "계란", "달걀", "두부",
        "삼겹", "한우", "돼지", "닭", "소고기", "고기", "수산", "생선",
        "조개", "미역", "김", "우유", "치즈", "버섯", "채소", "야채", "콩나물",
        "아보카도",
    ],
}


def apply_fallback_category(item: Dict[str, Any]) -> Optional[str]:
    """
    item 하나에 대해 fallback category를 반환한다.

    Returns:
        확정 가능한 카테고리면 category 문자열
        판단 불가하면 None
    """

    name = _normalize_text(item.get("name"))

    if not name:
        return None

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if _normalize_text(keyword) in name:
                return normalize_category(category)

    return None


def apply_fallback_category_by_name(name: str) -> Optional[str]:
    """
    상품명 문자열만으로 fallback category를 판단할 때 사용.
    """

    item = {"name": name}
    return apply_fallback_category(item)


def should_skip_llm(item: Dict[str, Any]) -> bool:
    """
    fallback으로 명확히 분류되면 LLM 호출을 생략할 수 있다.
    """

    return apply_fallback_category(item) is not None


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[^0-9a-zA-Z가-힣]", "", text)
    return text