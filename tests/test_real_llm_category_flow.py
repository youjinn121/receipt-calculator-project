import json
import os
from pathlib import Path

import pytest

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
        "001_costco semantic JSON을 찾지 못했습니다."
    )


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY 환경변수가 없어 실제 API 테스트를 건너뜁니다.",
)
def test_real_llm_costco_001_small_sample():
    semantic = _load_costco_001_semantic()

    # 비용 절감용: 실제 API는 5개 상품만 호출
    semantic = dict(semantic)
    semantic["items"] = semantic.get("items", [])[:5]

    result = categorize_receipt_items(
        semantic_receipt=semantic,
        use_llm=True,
        use_fallback=False,  # 평가 모드: fallback 끔
    )

    print("\n==============================")
    print("실제 GPT API 카테고리 결과")
    print("==============================")

    for item in result["items"]:
        print(
            f'{item["name"]} '
            f'| final={item.get("final_price")} '
            f'| category={item.get("category")} '
            f'| raw={item.get("category_meta", {}).get("raw_response")}'
        )

    print("\n==============================")
    print("Metrics")
    print("==============================")
    print(
        json.dumps(
            result.get("category_metrics", {}),
            ensure_ascii=False,
            indent=2,
        )
    )

    assert len(result["items"]) == 5

    for item in result["items"]:
        assert item["category"] in [
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

    assert result["category_metrics"]["total_items"] == 5