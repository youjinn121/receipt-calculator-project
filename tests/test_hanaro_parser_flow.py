from __future__ import annotations

from receipt_parser.parser_pipeline import parse_receipt


def test_hanaro_real_receipt_046():
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

    assert parsed["store"] == "hanaro"
    assert parsed["file_name"] == "046_hanaro.json"

    lines = parsed["lines"]
    assert len(lines) == 8

    line_types = [line["line_type"] for line in lines]

    # 핵심 타입 존재 여부
    assert line_types.count("item_name") == 3
    assert line_types.count("item_detail") == 3
    assert "subtotal" in line_types
    assert "total" in line_types

    # -------------------------
    # item_detail 검증
    # -------------------------
    item_details = [
        line for line in lines
        if line["line_type"] == "item_detail"
    ]

    # 1번 상품
    assert item_details[0]["code"] == "265405"
    assert item_details[0]["unit_price_raw"] == 17690
    assert item_details[0]["qty"] == 1
    assert item_details[0]["price_raw"] == 17690

    # 2번 상품
    assert item_details[1]["code"] == "253483"
    assert item_details[1]["unit_price_raw"] == 9650
    assert item_details[1]["qty"] == 1
    assert item_details[1]["price_raw"] == 9650

    # 3번 상품 (13자리 바코드)
    assert item_details[2]["code"] == "8801045352107"
    assert item_details[2]["unit_price_raw"] == 3060
    assert item_details[2]["qty"] == 1
    assert item_details[2]["price_raw"] == 3060

    # -------------------------
    # total 검증
    # -------------------------
    subtotal = next(
        line for line in lines
        if line["line_type"] == "subtotal"
    )
    total = next(
        line for line in lines
        if line["line_type"] == "total"
    )

    assert subtotal["price_raw"] == 30400
    assert total["price_raw"] == 30400

    # -------------------------
    # 상품 합계 = 총구매액
    # -------------------------
    computed_sum = sum(
        item["price_raw"] for item in item_details
    )

    assert computed_sum == 30400


if __name__ == "__main__":
    test_hanaro_real_receipt_046()
    print("046_hanaro parser test passed")