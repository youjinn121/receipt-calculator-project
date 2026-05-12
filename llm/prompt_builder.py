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

from llm.category_schema import (
    CATEGORY_DESCRIPTIONS,
    CATEGORY_PRIORITY_RULES,
    PRIMARY_CATEGORIES,
)


CATEGORY_CAUTION_RULES = """[주의 규칙]
- 상품명에 '동물'이라는 단어가 있어도 무조건 반려동물로 분류하지 않는다.
- '동물복지란', '자유방목복지란', '계란', '달걀', '유정란', '란'은 식품/계란류이므로 식재료로 분류한다.
- 상품명에 '우유'가 포함된 기본 우유류는 식재료로 분류한다.
- 땅콩버터, 피넛버터, 스프레드류는 식사용 소비 및 식사 재료 성격이 강하므로 식재료로 분류한다.
- 유기농 우유, 비타민우유, 강화우유, 일반 우유, 흰우유, 컵우유, 3컵우유는 식재료로 분류한다.
- 커피우유, 초코우유, 딸기우유, 바나나우유처럼 향미/가공 음료 성격이 명확한 우유음료는 음료로 분류한다.
- 마시는 요거트, 요구르트음료는 음료로 분류한다.
- 그릭요거트, 무가당요거트, 플레인요거트는 식재료로 분류한다.
- 생크림요거트, 떠먹는 요거트처럼 디저트/간식 성격이 강한 요거트는 간식으로 분류한다.
- 고추튀김, 튀김류는 간편식으로 분류한다.
- 꿀약과, 약과는 간식으로 분류한다.
- 랩, 주방랩, 프레스앤씰은 생활용품으로 분류한다.
- 버터, 메이플버터는 식재료로 분류한다.
- 테라(페트), 테라 맥주는 음료가 아니라 주류로 분류한다.
- 바나나, 사과, 배, 귤, 딸기 등 과일류는 식재료로 분류한다.
- 칫솔, 치약, 샴푸, 린스, 바디워시, 비누는 생활용품으로 분류한다.
- 핫도그, 순댓국, 국/탕류, 전골류, 초밥, 볶음밥은 간편식으로 분류한다.
- 후추, 소금, 설탕, 식초, 간장, 고추장, 된장, 시즈닝, 향신료, 소스류는 식재료로 분류한다.
- 잼, 스프레드류는 식사용/재료 성격이 강하면 식재료로 분류한다.
- 누텔라처럼 디저트/간식 성격이 강한 스프레드는 간식으로 분류한다.
- 드레싱, 샐러드드레싱, 소스류는 식재료로 분류한다.
- 비피더스, 요구르트음료, 마시는 요거트는 음료로 분류한다.
- 면봉은 생활용품으로 분류한다.
- 치킨너겟, 통살치킨, 튀김류는 간편식으로 분류한다.
- 집밥 자립도 관점에서 완제품 반찬류, 김치 완제품, 젓갈류, 장조림, 회, 초밥은 직접 조리 원재료가 아니라 간편식으로 분류한다.
- 단, 생고기, 생닭, 생연어, 수산물 원물, 건어물, 황태채처럼 직접 조리하거나 손질해 먹는 원재료는 식재료로 분류한다.
- 샴푸, 린스, 바디워시, 비누, 치약, 칫솔은 생활용품으로 분류한다.
- 세제, 세탁세제, 섬유유연제, 락스 등은 생활용품으로 분류한다.
- 고무장갑은 생활용품으로 분류한다.
- 의류, 반소매, 티셔츠, 파자마, 자켓, 신발은 기타로 분류한다.
- 타월, 수건, 휴지, 티슈는 생활용품으로 분류한다.
- 종량제봉투, 쓰레기봉투는 생활용품으로 분류한다.
- 컨디션스틱, 숙취해소제, 기능성 스틱 제품은 기타로 분류한다.
- '반려동물'은 사료, 반려동물 간식, 배변패드, 고양이 모래, 반려동물 장난감처럼 반려동물 사용 목적이 명확한 상품에만 사용한다.
- 의류, 자켓, 신발, 전자제품, 잡화, 공구, 망치는 기타로 분류한다.
- 필라이트, 테라, 카스, 하이네켄, 맥주, 동동주, 막걸리, 소주, 와인은 주류로 분류한다.
- 단, 카스테라/제과/디저트 문맥 또는 '샹달프& 카스'처럼 식품 조합으로 보이는 경우에는 주류보다 간식/식재료 문맥을 우선한다.
- 재사용봉투, 쇼핑봉투, 장바구니봉투, 봉투20L은 생활용품으로 분류한다.
- 글라스락, 그리들, 팬, 냄비, 프라이팬 등 주방 조리도구는 생활용품으로 분류한다.
- 식재료일 가능성이 높더라도 상품명만으로 확정 가능한 수준이 아니면 기타 허용 가능하다.
- 핵심 소비 목적 키워드가 상품명에 직접 존재하는지 우선 확인한다.
- 브랜드명이나 외부 지식에 과도하게 의존해서 소비 목적을 추론하지 않는다.
- OCR 축약이 심하거나 의미 복원이 필요한 경우 보수적으로 판단한다.

- 식빵, 피타브레드, 또띠아처럼 식사용 베이스 성격이 강한 빵류는 식재료로 분류한다.
- 샹달프, 잼, 스프레드류는 식사용/재료 성격이 강하면 식재료로 분류한다.
- 그릭요거트, 무가당요거트, 플레인요거트는 식사용/재료 성격이 강하므로 식재료로 분류한다.
- 피클은 반찬/가니시 또는 식사 재료 성격이 강하므로 식재료로 분류한다.
- 동치미육수, 육수류는 조리/식사 베이스 성격이 강하므로 식재료로 분류한다.
- 포크립, 포크 립처럼 육류 원재료로 보이는 상품은 식재료로 분류한다.
- 후추, 통후추, 조미료, 향신료는 식재료로 분류한다.

- 홍어회, 홍어회 모둠처럼 이미 손질되어 바로 먹는 회류는 간편식으로 분류한다.

- 아카페라처럼 RTD 커피/커피 음료 성격이 명확한 상품은 음료로 분류한다.

- ORALB, 오랄비, KIDS TB, 액츠, 액츠데오후레쉬처럼 브랜드/축약 지식에 의존해야 하는 상품은 생활용품으로 강제하지 않고 기타 허용 가능하다.
- 수정테이프, 필기구, 문구류, 사무용품은 생활용품이 아니라 기타로 분류한다.
- 맛타리, 오이스터블처럼 식재료 가능성은 있으나 핵심 키워드가 생략된 상품은 기타 허용 가능하다.
- 맥심오리지날리필, 엔요처럼 음료 가능성은 있으나 상품명만으로 확정이 어려운 축약 상품은 기타 허용 가능하다.
- 상품명이 짧은 한글 토큰으로 부자연스럽게 분리되어 있고, 완제품/즉석식/조리식 키워드가 명확하지 않으면 간편식으로 분류하지 않는다.
- 예: "오뚜기 순 후 추"처럼 조미료로 복원될 가능성이 있지만 OCR 분절로 의미가 불명확한 경우, 간편식이 아니라 식재료 또는 기타로 분류한다.
- 간편식은 라면, 만두, 볶음밥, 반찬류, 국/탕, 회, 즉석식품처럼 완제품 소비 목적이 상품명에 직접 드러날 때만 사용한다.
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
출력은 카테고리명 하나만 작성한다.

[허용 카테고리]
{category_list}

[카테고리 설명]
{category_description_text}

{CATEGORY_PRIORITY_RULES}

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
3. [중요 분류 우선 규칙]에 해당하는 상품은 반드시 해당 카테고리로 분류한다.
4. 우선 규칙에 해당하는 상품을 '기타'로 보내지 않는다.
5. 상품의 브랜드명이 아니라 주 사용 목적을 기준으로 분류한다.
6. 상품명만으로 애매하면 구매처, 가격, 수량, 같이 구매한 상품을 참고한다.
7. 판단이 어렵지만 소비재 유형이 명확하면 Uncategorized보다 가장 가까운 허용 카테고리를 선택한다.
8. 정말 판단 불가이거나 허용 카테고리로 분류할 수 없을 때만 Uncategorized를 출력한다.
9. 의류, 가구, 문구, 잡화, 공구처럼 현재 소비 분석 카테고리에 들어가지 않는 항목만 기타로 분류한다.
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

    basket_names = [
        _safe_str(item.get("name"))
        for item in items
        if _safe_str(item.get("name"))
    ]
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

반드시 아래 허용 카테고리 중 하나만 선택해야 한다.

[허용 카테고리]
{category_list}

[카테고리 설명]
{category_description_text}

{CATEGORY_PRIORITY_RULES}

{CATEGORY_CAUTION_RULES}

[구매처]
{store}

[장바구니 전체 문맥]
{basket_context}

[분류 대상 상품 목록]
{chr(10).join(item_lines)}

[출력 규칙]
1. 각 상품 번호에 대해 허용 카테고리 중 하나만 선택한다.
2. [중요 분류 우선 규칙]에 해당하는 상품은 반드시 해당 카테고리로 분류한다.
3. 우선 규칙에 해당하는 상품을 '기타'로 보내지 않는다.
4. 출력은 JSON 배열만 작성한다.
5. 각 원소는 {{"index": 번호, "category": "카테고리"}} 형식이어야 한다.
6. 허용되지 않은 카테고리나 진짜 판단 불가는 Uncategorized로 처리한다.
7. 설명 문장을 출력하지 않는다.

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