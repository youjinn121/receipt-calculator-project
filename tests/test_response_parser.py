from llm.response_parser import (
    parse_category_response,
    parse_batch_category_response,
)


def test_parse_category_response_exact_category():
    assert parse_category_response("식재료") == "식재료"
    assert parse_category_response("간편식") == "간편식"
    assert parse_category_response("주류") == "주류"


def test_parse_category_response_with_noise():
    assert parse_category_response('"간식"') == "간식"
    assert parse_category_response("음료.") == "음료"
    assert parse_category_response("```생활용품```") == "생활용품"


def test_parse_category_response_json_object():
    raw = '{"category": "반려동물"}'
    assert parse_category_response(raw) == "반려동물"


def test_parse_category_response_embedded_text():
    assert parse_category_response("이 상품은 식재료로 분류됩니다.") == "식재료"


def test_parse_category_response_invalid_returns_uncategorized():
    assert parse_category_response(None) == "Uncategorized"
    assert parse_category_response("") == "Uncategorized"
    assert parse_category_response("자동차용품") == "Uncategorized"
    assert parse_category_response('{"category": "없는카테고리"}') == "Uncategorized"


def test_parse_batch_category_response_json_array():
    raw = """
    [
      {"index": 1, "category": "식재료"},
      {"index": 2, "category": "간식"},
      {"index": 3, "category": "주류"}
    ]
    """

    result = parse_batch_category_response(
        raw_response=raw,
        expected_count=3,
    )

    assert result == ["식재료", "간식", "주류"]


def test_parse_batch_category_response_missing_items_filled_uncategorized():
    raw = """
    [
      {"index": 1, "category": "식재료"}
    ]
    """

    result = parse_batch_category_response(
        raw_response=raw,
        expected_count=3,
    )

    assert result == ["식재료", "Uncategorized", "Uncategorized"]


def test_parse_batch_category_response_invalid_category():
    raw = """
    [
      {"index": 1, "category": "식재료"},
      {"index": 2, "category": "없는카테고리"}
    ]
    """

    result = parse_batch_category_response(
        raw_response=raw,
        expected_count=2,
    )

    assert result == ["식재료", "Uncategorized"]


def test_parse_batch_category_response_line_fallback():
    raw = """
    1. 식재료
    2. 간식
    3. 생활용품
    """

    result = parse_batch_category_response(
        raw_response=raw,
        expected_count=3,
    )

    assert result == ["식재료", "간식", "생활용품"]