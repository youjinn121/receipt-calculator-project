import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from pprint import pprint

from validation.validator import validate_receipt


def run_qty_validation_test():
    """
    unit_price × qty 검증 테스트

    1. 정상 케이스
    2. 오류 케이스
    """

    # =========================
    # ✅ 정상 케이스
    # =========================
    correct_case = {
        "file_name": "test_correct.json",
        "store": "costco",
        "items": [
            {
                "name": "정상 상품",
                "code": "111",
                "qty": 2,
                "unit_price": 1000,
                "base_price": 2000,   # 정상
                "discount": 0,
                "final_price": 2000,
            }
        ],
        "tail_info": {
            "total_lines": [
                {"price_raw": 2000}
            ]
        }
    }

    # =========================
    # ❌ 오류 케이스 (qty mismatch)
    # =========================
    wrong_case = {
        "file_name": "test_wrong.json",
        "store": "costco",
        "items": [
            {
                "name": "오류 상품",
                "code": "222",
                "qty": 2,
                "unit_price": 1000,
                "base_price": 1800,   # ❌ 틀림 (정상은 2000)
                "discount": 0,
                "final_price": 1800,
            }
        ],
        "tail_info": {
            "total_lines": [
                {"price_raw": 1800}
            ]
        }
    }

    print("\n" + "=" * 80)
    print("✅ CORRECT CASE")
    print("=" * 80)

    result1 = validate_receipt(correct_case)
    pprint(result1, sort_dicts=False)

    print("\n" + "=" * 80)
    print("❌ WRONG CASE (qty mismatch)")
    print("=" * 80)

    result2 = validate_receipt(wrong_case)
    pprint(result2, sort_dicts=False)

    # =========================
    # 핵심 체크
    # =========================

    print("\n" + "=" * 80)
    print("🔍 ASSERT CHECK")
    print("=" * 80)

    # 정상 케이스 → warning 없어야 함
    if len(result1["warnings"]) == 0:
        print("✔ 정상 케이스: OK (warning 없음)")
    else:
        print("❌ 정상 케이스: 이상 있음")

    # 오류 케이스 → warning 있어야 함
    if any("unit_price * qty != base_price" in w["reason"] for w in result2["warnings"]):
        print("✔ 오류 케이스: OK (warning 발생)")
    else:
        print("❌ 오류 케이스: 검증 실패")


if __name__ == "__main__":
    run_qty_validation_test()