import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from pprint import pprint

from receipt_parser.parser_pipeline import parse_receipt
from semantic.interpreter import interpret_receipt
from validation.validator import validate_receipt


def run_costco_validation_test():
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
            "합계 (VAT 포함) 19,780",
        ],
    }

    parsed = parse_receipt(receipt, store="costco")
    semantic_result = interpret_receipt(parsed)
    validation_result = validate_receipt(semantic_result)

    print("\n" + "=" * 80)
    print("VALIDATION RESULT")
    print("=" * 80)
    pprint(validation_result, sort_dicts=False)


if __name__ == "__main__":
    run_costco_validation_test()