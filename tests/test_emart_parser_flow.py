from __future__ import annotations

import json
from pprint import pprint

from receipt_parser.parser_pipeline import parse_receipt


def build_emart_receipt_026() -> dict:
    return {
        "file_name": "026_emart.json",
        "store": "emart",
        "lines": [
            "상품명 단 가 수량 금 액",
            "01* 5K프라이스 3컵우유",
            "8801121027097 1,450 1 1,450",
            "02 오뚜기 컵밥 옛날 잡",
            "8801045061047 4,980 1 4,980",
            "컵밥류 2+1 -1,660",
            "03 오뚜기 특양지설렁탕",
            "8801045370767 4,980 2 9,960",
            "컵밥류 2+1 -3,320",
            "04 5K 김치 수제비",
            "8809083708832 1,980 2 3,960",
            "(*)면세 물품 1,450",
            "과세 물품 12,655",
            "부 가 세 1,265",
            "합 계 15,370",
            "결제대상금액 15,370",
        ],
    }


def build_emart_receipt_027() -> dict:
    return {
        "file_name": "027_emart.json",
        "store": "emart",
        "lines": [
            "상품명 단 가 수량 금 액",
            "01 떡붕어싸만코",
            "8801104306928 2,000 5 10,000",
            "샌드류5개5천 -5,000",
            "02 롯데 월드콘 말차 160",
            "8802259025351 2,000 1 2,000",
            "과세 물품 6,364",
            "부 가 세 636",
            "합 계 7,000",
            "결제대상금액 7,000",
        ],
    }


def run_case(receipt: dict) -> None:
    result = parse_receipt(receipt, store="emart")

    print("=" * 100)
    print(f"[CASE] {receipt['file_name']}")
    print("=" * 100)

    for row in result["lines"]:
        print(
            f"[{row['line_idx']:02d}] "
            f"type={row['line_type']:<16} "
            f"text={row['line_text']!r}"
        )
        print(
            f"     normalized={row['normalized_line_text']!r} | "
            f"code={row['code']!r}, qty={row['qty']!r}, "
            f"unit_price_raw={row['unit_price_raw']!r}, "
            f"price_raw={row['price_raw']!r}, "
            f"discount_raw={row['discount_raw']!r}, "
            f"name_raw={row['name_raw']!r}"
        )

    print("\n[JSON]")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()


def main() -> None:
    run_case(build_emart_receipt_026())
    run_case(build_emart_receipt_027())


if __name__ == "__main__":
    main()