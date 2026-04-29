from semantic.semantic_manager import interpret_receipt
from receipt_parser.parser_pipeline import parse_receipt


def test_hanaro_semantic_basic_flow():
    receipt = {
        "file_name": "046_hanaro.json",
        "store": "hanaro",
        "lines": [
            "상품(코드) 단가 수량 금액",
            "001 P삼겹살",
            "*265405 17,690 1 17,690",
            "002 P한우사태",
            "*253483 9,650 1 9,650",
            "003 P옛날자른미역 (50g) 50g*30",
            "*8801045352107 3,060 1 3,060",
            "총구매액: 30,400",
            "내실금액: 30,400",
        ],
    }

    parsed = parse_receipt(receipt, store="hanaro")
    result = interpret_receipt(parsed, store="hanaro")

    assert result["store"] == "hanaro"

    items = result["items"]
    assert len(items) == 3

    # 첫 상품
    assert items[0]["name"] == "P삼겹살"
    assert items[0]["code"] == "265405"
    assert items[0]["qty"] == 1
    assert items[0]["base_price"] == 17690
    assert items[0]["final_price"] == 17690

    # 두 번째
    assert items[1]["code"] == "253483"
    assert items[1]["base_price"] == 9650

    # 세 번째 바코드
    assert items[2]["code"] == "8801045352107"
    assert items[2]["base_price"] == 3060

    # tail summary
    summary = result["tail_info"]["summary"]

    assert summary["item_total"] == 30400
    assert summary["payment_total"] == 30400