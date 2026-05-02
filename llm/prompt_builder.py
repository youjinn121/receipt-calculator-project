"""
[Prompt Builder]

상품 카테고리 정규화를 위한 LLM 프롬프트 생성 모듈.

입력:
- semantic item 객체
- store
- 같은 영수증 내 장바구니 상품명 목록

출력:
- LLM에 전달할 prompt 문자열

원칙:
- LLM은 사전 정의된 카테고리 중 하나만 선택해야 한다.
- 상품명만 보지 않고 구매처, 가격, 수량, 장바구니 문맥을 함께 제공한다.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from llm.category_schema import CATEGORY_DESCRIPTIONS, PRIMARY_CATEGORIES

CATEGORY_CAUTION_RULES = """[주의 규칙]
- 상품명에 '동물'이라는 단어가 있어도 무조건 반려동물로 분류하지 않는다.
- '동물복지란', '계란', '달걀', '유정란', '란'은 식품/계란류이므로 식재료로 분류한다.
- '반려동물'은 사료, 반려동물 간식, 배변패드, 고양이 모래, 반려동물 장난감처럼 반려동물 사용 목적이 명확한 상품에만 사용한다.
- 의류, 자켓, 신발, 전자제품, 잡화는 기타로 분류한다.
"""


def build_category_prompt(
    item: Dict[str, Any],
    store: str,
    basket_items: Optional[Iterable[str]] = None,
) -> str:
    item_name = _safe_str(item.get("name"))
    unit_price = _safe_int(item.get("unit_price"))
    qty = _safe_int(item.get("qty"))
    base_price = _safe_int(item.get("base_price"))
    discount = _safe_int(item.get("discount")) or 0
    final_price = _safe_int(item.get("final_price"))

    basket_context = _format_basket_items(
        basket_items=basket_items,
        current_item_name=item_name,
    )

    category_list = ", ".join(PRIMARY_CATEGORIES)
    category_description_text = _format_category_descriptions()

    return f"""너는 마트 영수증 상품을 소비 분석용 카테고리로 분류하는 보조 모델이다.

반드시 아래 허용 카테고리 중 하나만 선택해야 한다.

[허용 카테고리]
{category_list}

[카테고리 설명]
{category_description_text}

{CATEGORY_CAUTION_RULES}

[분류 대상 상품]
- 상품명: {item_name}
- 구매처: {store}
- 수량: {_format_optional_number(qty)}
- 단가: {_format_money(unit_price)}
- 할인 전 금액: {_format_money(base_price)}
- 할인 금액: {_format_money(discount)}
- 최종 금액: {_format_money(final_price)}

[같이 구매한 상품]
{basket_context}

[분류 규칙]
1. 출력은 반드시 허용 카테고리 중 하나만 작성한다.
2. 설명, 문장, 따옴표, 마크다운, JSON을 출력하지 않는다.
3. 판단이 어렵거나 허용 카테고리에 맞지 않으면 Uncategorized를 출력한다.
4. 상품명만으로 애매하면 구매처, 가격, 수량, 같이 구매한 상품을 참고한다.
5. 술, 맥주, 소주, 막걸리, 와인 등은 반드시 주류로 분류한다.
6. 라면, 컵밥, 냉동식품, 즉석식품, 반찬류는 간편식으로 분류한다.
7. 과자, 빵, 아이스크림, 디저트는 간식으로 분류한다.
8. 채소, 과일, 육류, 수산물, 달걀, 계란, 유정란, 동물복지란, 두부 등 조리 재료는 식재료로 분류한다.
9. 상품명에 동물이라는 단어가 포함되어도 계란류이면 반려동물이 아니라 식재료로 분류한다.
10. 반려동물은 반려동물용 상품임이 명확할 때만 선택한다.

카테고리만 답변하라."""
    

def build_batch_category_prompt(
    items: List[Dict[str, Any]],
    store: str,
) -> str:
    """
    여러 상품을 한 번에 분류할 때 사용할 프롬프트.
    초기 구현은 단건 분류를 권장하지만, 비용 절감이 필요하면 이 함수 사용.
    """

    category_list = ", ".join(PRIMARY_CATEGORIES)
    category_description_text = _format_category_descriptions()

    basket_names = [_safe_str(item.get("name")) for item in items if _safe_str(item.get("name"))]
    basket_context = _format_basket_items(basket_names)

    item_lines = []
    for idx, item in enumerate(items, start=1):
        item_lines.append(
            f"{idx}. 상품명={_safe_str(item.get('name'))}, "
            f"수량={_format_optional_number(_safe_int(item.get('qty')))}, "
            f"단가={_format_money(_safe_int(item.get('unit_price')))}, "
            f"최종금액={_format_money(_safe_int(item.get('final_price')))}"
        )

    return f"""너는 마트 영수증 상품을 소비 분석용 카테고리로 분류하는 보조 모델이다.

[허용 카테고리]
{category_list}

[카테고리 설명]
{category_description_text}

{CATEGORY_CAUTION_RULES}

[구매처]
{store}

[장바구니 전체 문맥]
{basket_context}

[분류 대상 상품 목록]
{chr(10).join(item_lines)}

[출력 규칙]
1. 각 상품 번호에 대해 허용 카테고리 중 하나만 선택한다.
2. 출력은 JSON 배열만 작성한다.
3. 각 원소는 {{"index": 번호, "category": "카테고리"}} 형식이어야 한다.
4. 허용되지 않은 카테고리나 판단 불가는 Uncategorized로 처리한다.
5. 설명 문장을 출력하지 않는다.

JSON 배열만 답변하라."""


def _format_category_descriptions() -> str:
    lines = []

    for category in PRIMARY_CATEGORIES:
        description = CATEGORY_DESCRIPTIONS.get(category, "")
        lines.append(f"- {category}: {description}")

    return "\n".join(lines)


def _format_basket_items(
    basket_items: Optional[Iterable[str]],
    current_item_name: Optional[str] = None,
    max_items: int = 12,
) -> str:
    if not basket_items:
        return "없음"

    current = _safe_str(current_item_name)
    cleaned: List[str] = []

    for name in basket_items:
        text = _safe_str(name)
        if not text:
            continue

        if current and text == current:
            continue

        if text not in cleaned:
            cleaned.append(text)

        if len(cleaned) >= max_items:
            break

    if not cleaned:
        return "없음"

    return ", ".join(cleaned)


def _format_money(value: Optional[int]) -> str:
    if value is None:
        return "알 수 없음"

    return f"{value:,}원"


def _format_optional_number(value: Optional[int]) -> str:
    if value is None:
        return "알 수 없음"

    return f"{value:,}"


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None

    try:
        return int(value)
    except Exception:
        return None


def _safe_str(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()