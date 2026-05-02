import json
from pathlib import Path

from llm.category_manager import categorize_receipt_items


def _load_costco_001_semantic():
    candidates = [
        Path("data/semantic/costco/001_costco.json"),
        Path("tests/fixtures/001_costco_semantic.json"),
    ]

    for path in candidates:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)

    raise FileNotFoundError(
        "001_costco semantic JSON을 찾지 못했습니다. "
        "data/semantic/costco/001_costco.json 또는 "
        "tests/fixtures/001_costco_semantic.json 위치에 저장하세요."
    )


def _fake_call_llm(prompt: str, *args, **kwargs):
    target_name = ""

    for line in prompt.splitlines():
        line = line.strip()

        if line.startswith("- 상품명:"):
            target_name = line.replace("- 상품명:", "").strip()
            break

    mapping = {
        "카스375MLX20캔": "주류",
        "프렌치버터크라상": "간식",
        "COLUMBIA 남성 자켓": "기타",
        "유기농 우유": "식재료",
        "백오이 1봉": "식재료",
        "봉지굴 (대) 500G": "식재료",
        "정통어묵탕모듬": "간편식",
        "무농약 콩나물": "식재료",
        "동물복지란30구": "식재료",
        "국산돈육통삼겹": "식재료",
        "아보카도 6개": "식재료",
    }

    return mapping.get(target_name, "Uncategorized")


def test_costco_001_llm_category_flow_mock(monkeypatch):
    """
    평가 모드:
    - use_fallback=False
    - use_llm=True
    - 실제 API 호출은 mock 처리
    """

    monkeypatch.setattr(
        "llm.category_manager.call_llm",
        _fake_call_llm,
    )

    semantic = _load_costco_001_semantic()

    result = categorize_receipt_items(
        semantic_receipt=semantic,
        use_llm=True,
        use_fallback=False,
    )

    items = result["items"]

    assert len(items) == 11

    categories = {
        item["name"]: item["category"]
        for item in items
    }

    assert categories["카스375MLX20캔"] == "주류"
    assert categories["프렌치버터크라상"] == "간식"
    assert categories["COLUMBIA 남성 자켓"] == "기타"
    assert categories["유기농 우유"] == "식재료"
    assert categories["정통어묵탕모듬"] == "간편식"
    assert categories["국산돈육통삼겹"] == "식재료"

    for item in items:
        assert item["category_meta"]["method"] == "llm"
        assert item["category_meta"]["use_fallback"] is False
        assert item["category_meta"]["use_llm"] is True

    assert result["category_summary"]["식재료"]["item_count"] == 7
    assert result["category_summary"]["간식"]["item_count"] == 1
    assert result["category_summary"]["간편식"]["item_count"] == 1
    assert result["category_summary"]["주류"]["item_count"] == 1
    assert result["category_summary"]["기타"]["item_count"] == 1

    metrics = result["category_metrics"]
    assert metrics["total_items"] == 11
    assert metrics["categorized_items"] == 11
    assert metrics["uncategorized_items"] == 0
    assert metrics["coverage_rate"] == 100.0
    assert metrics["method_counts"]["llm"] == 11
    assert metrics["method_counts"]["fallback"] == 0


def test_costco_001_operating_mode_with_fallback(monkeypatch):
    """
    운영 모드:
    - use_fallback=True
    - fallback으로 처리 가능한 상품은 LLM 호출 생략
    - fallback 실패 상품만 LLM 호출
    """

    monkeypatch.setattr(
        "llm.category_manager.call_llm",
        _fake_call_llm,
    )

    semantic = _load_costco_001_semantic()

    result = categorize_receipt_items(
        semantic_receipt=semantic,
        use_llm=True,
        use_fallback=True,
    )

    items = result["items"]

    assert len(items) == 11

    categories = {
        item["name"]: item["category"]
        for item in items
    }

    assert categories["카스375MLX20캔"] == "주류"
    assert categories["프렌치버터크라상"] == "간식"
    assert categories["COLUMBIA 남성 자켓"] == "기타"
    assert categories["유기농 우유"] == "식재료"
    assert categories["정통어묵탕모듬"] == "간편식"

    method_counts = result["category_metrics"]["method_counts"]

    assert method_counts["fallback"] >= 1
    assert method_counts["llm"] >= 1
    assert method_counts["fallback"] + method_counts["llm"] == 11

    # fallback에 없는 COLUMBIA는 LLM으로 처리되어야 함
    columbia = next(
        item for item in items
        if item["name"] == "COLUMBIA 남성 자켓"
    )
    assert columbia["category"] == "기타"
    assert columbia["category_meta"]["method"] == "llm"


def test_costco_001_category_flow_disabled_mode():
    """
    비활성 모드:
    - use_llm=False
    - use_fallback=False
    - 전부 Uncategorized
    """

    semantic = _load_costco_001_semantic()

    result = categorize_receipt_items(
        semantic_receipt=semantic,
        use_llm=False,
        use_fallback=False,
    )

    items = result["items"]

    assert len(items) == 11

    for item in items:
        assert item["category"] == "Uncategorized"
        assert item["category_meta"]["method"] == "disabled"

    metrics = result["category_metrics"]
    assert metrics["total_items"] == 11
    assert metrics["categorized_items"] == 0
    assert metrics["uncategorized_items"] == 11
    assert metrics["coverage_rate"] == 0.0
    assert metrics["uncategorized_rate"] == 100.0


def test_costco_001_category_flow_print_result(monkeypatch):
    """
    결과 확인용 출력 테스트.
    실행 시 -s 옵션을 붙이면 출력 확인 가능.

    python -m pytest tests/test_llm_category_flow.py -v -s
    """

    monkeypatch.setattr(
        "llm.category_manager.call_llm",
        _fake_call_llm,
    )

    semantic = _load_costco_001_semantic()

    result = categorize_receipt_items(
        semantic_receipt=semantic,
        use_llm=True,
        use_fallback=False,
    )

    print("\n==============================")
    print("상품별 카테고리 결과")
    print("==============================")

    for item in result["items"]:
        print(
            f'{item["name"]} '
            f'| qty={item.get("qty")} '
            f'| final={item.get("final_price")} '
            f'| category={item.get("category")} '
            f'| method={item.get("category_meta", {}).get("method")}'
        )

    print("\n==============================")
    print("카테고리 Summary")
    print("==============================")
    print(
        json.dumps(
            result.get("category_summary", {}),
            ensure_ascii=False,
            indent=2,
        )
    )

    print("\n==============================")
    print("카테고리 Metrics")
    print("==============================")
    print(
        json.dumps(
            result.get("category_metrics", {}),
            ensure_ascii=False,
            indent=2,
        )
    )

    assert result["category_metrics"]["total_items"] == 11