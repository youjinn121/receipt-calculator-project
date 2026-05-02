from llm.prompt_builder import build_category_prompt, build_batch_category_prompt
from llm.category_schema import PRIMARY_CATEGORIES


def test_build_category_prompt_contains_core_context():
    item = {
        "name": "카스375MLX20캔",
        "qty": 1,
        "unit_price": 25490,
        "base_price": 25490,
        "discount": 0,
        "final_price": 25490,
    }

    prompt = build_category_prompt(
        item=item,
        store="costco",
        basket_items=["카스375MLX20캔", "프렌치버터크라상", "국산돈육통삼겹"],
    )

    assert "상품명: 카스375MLX20캔" in prompt
    assert "구매처: costco" in prompt
    assert "단가: 25,490원" in prompt
    assert "최종 금액: 25,490원" in prompt
    assert "프렌치버터크라상" in prompt
    assert "국산돈육통삼겹" in prompt

    # 현재 상품명은 같이 구매한 상품 문맥에서 제외되어야 함
    basket_section = prompt.split("[같이 구매한 상품]")[-1]
    assert basket_section.count("카스375MLX20캔") == 0

    for category in PRIMARY_CATEGORIES:
        assert category in prompt


def test_build_category_prompt_handles_missing_values():
    item = {
        "name": "알수없는상품",
        "final_price": None,
    }

    prompt = build_category_prompt(
        item=item,
        store="emart",
        basket_items=[],
    )

    assert "상품명: 알수없는상품" in prompt
    assert "구매처: emart" in prompt
    assert "알 수 없음" in prompt
    assert "없음" in prompt
    assert "카테고리만 답변하라" in prompt


def test_build_batch_category_prompt_contains_json_rule():
    items = [
        {
            "name": "삼겹살",
            "qty": 1,
            "unit_price": 10000,
            "final_price": 10000,
        },
        {
            "name": "라면",
            "qty": 2,
            "unit_price": 1000,
            "final_price": 2000,
        },
    ]

    prompt = build_batch_category_prompt(
        items=items,
        store="hanaro",
    )

    assert "구매처" in prompt
    assert "hanaro" in prompt
    assert "삼겹살" in prompt
    assert "라면" in prompt
    assert '"index"' in prompt
    assert '"category"' in prompt
    assert "JSON 배열만 답변하라" in prompt