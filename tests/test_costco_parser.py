import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from pprint import pprint

from receipt_parser.parser_pipeline import parse_receipt


def run_costco_parser_test() -> None:
    """
    Costco 최소 테스트 세트
    현재 목표:
    - noise
    - item_name
    - item_detail
    - discount_keyword
    - discount_target
    - discount_detail
    - total
    확인
    """

    receipt = {
        "file_name": "001_costco.json",
        "file_meta": {},
        "lines": [
            "판매",
            "** Begin Bottom of Basket",
            "** Bottom Of Basket Item Count 0",
            "유기농 우유",
            "650635 1x 9,590 9,590",
            "CPN",
            "유기농우유 IRC",
            "11816 1x 1,800 1,800-",
            "아보카도 6개",
            "675741 1x 11,990 11,990",
            "상품수 소계 : 1",
            "면세 115,060",
            "과세 106,609",
            "부가세 10,661",
            "합계 (VAT 포함) 232,330",
        ],
    }

    result = parse_receipt(receipt, store="costco")

    print("\n" + "=" * 80)
    print("COSTCO PARSER TEST RESULT")
    print("=" * 80)

    for line in result["lines"]:
        print(f"[line_idx] {line['line_idx']}")
        print(f"  line_text            : {line['line_text']}")
        print(f"  normalized_line_text : {line['normalized_line_text']}")
        print(f"  line_type            : {line['line_type']}")
        print(f"  code                 : {line['code']}")
        print(f"  qty                  : {line['qty']}")
        print(f"  unit_price_raw       : {line['unit_price_raw']}")
        print(f"  price_raw            : {line['price_raw']}")
        print(f"  discount_raw         : {line['discount_raw']}")
        print(f"  name_raw             : {line['name_raw']}")
        print("-" * 80)

    print("\n" + "=" * 80)
    print("FULL RESULT")
    print("=" * 80)
    pprint(result, sort_dicts=False)


if __name__ == "__main__":
    run_costco_parser_test()