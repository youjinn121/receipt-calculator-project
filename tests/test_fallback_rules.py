from llm.fallback_rules import (
    apply_fallback_category,
    apply_fallback_category_by_name,
    should_skip_llm,
)


def test_fallback_category_alcohol():
    item = {"name": "카스375MLX20캔"}
    assert apply_fallback_category(item) == "주류"
    assert should_skip_llm(item) is True


def test_fallback_category_ingredient():
    assert apply_fallback_category_by_name("국산돈육통삼겹") == "식재료"
    assert apply_fallback_category_by_name("무농약 콩나물") == "식재료"
    assert apply_fallback_category_by_name("아보카도 6개") == "식재료"


def test_fallback_category_convenience_food():
    assert apply_fallback_category_by_name("신라면 멀티팩") == "간편식"
    assert apply_fallback_category_by_name("냉동만두") == "간편식"


def test_fallback_category_snack():
    assert apply_fallback_category_by_name("프렌치버터크라상") == "간식"
    assert apply_fallback_category_by_name("초코쿠키") == "간식"


def test_fallback_category_drink():
    assert apply_fallback_category_by_name("코카콜라 제로") == "음료"
    assert apply_fallback_category_by_name("생수 2L") == "음료"


def test_fallback_category_living_goods():
    assert apply_fallback_category_by_name("물티슈 캡형") == "생활용품"
    assert apply_fallback_category_by_name("주방세제") == "생활용품"


def test_fallback_category_pet():
    assert apply_fallback_category_by_name("고양이 사료") == "반려동물"
    assert apply_fallback_category_by_name("강아지 배변패드") == "반려동물"


def test_fallback_unknown_returns_none():
    item = {"name": "COLUMBIA 남성 자켓"}
    assert apply_fallback_category(item) is None
    assert should_skip_llm(item) is False


def test_fallback_empty_name_returns_none():
    assert apply_fallback_category({"name": ""}) is None
    assert apply_fallback_category({"name": None}) is None