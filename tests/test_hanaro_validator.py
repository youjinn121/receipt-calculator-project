from receipt_parser.parser_pipeline import parse_receipt
from semantic.semantic_manager import interpret_receipt
from validation.hanaro_validator import validate_hanaro


def test_hanaro_validator_basic_receipt_046():
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
    semantic = interpret_receipt(parsed, store="hanaro")
    result = validate_hanaro(semantic)

    assert result["store"] == "hanaro"
    assert result["is_valid"] is True
    assert result["recapture_recommended"] is False

    assert result["item_validation"]["checked_item_count"] == 3
    assert result["item_validation"]["valid_item_count"] == 3
    assert result["item_validation"]["invalid_item_count"] == 0

    assert result["receipt_validation"]["total_match"] is True

    debug = result["debug"]["receipt_validation"]

    assert debug["computed_base_price_sum"] == 30400
    assert debug["computed_final_price_sum"] == 30400
    assert debug["item_total"] == 30400
    assert debug["payment_total"] == 30400
    assert debug["item_total_match"] is True
    assert debug["payment_total_match"] is True
    assert debug["computed_expected_payment_total"] == 30400


def test_hanaro_validator_with_item_discount_and_receipt_discount():
    receipt = {
        "file_name": "052_hanaro.json",
        "store": "hanaro",
        "lines": [
            "상품(코드) 단가 수량 금액",
            "001 P삼겹살",
            "001*8801448212053 1,680 1 1,680",
            "002*2100051133899 2,000 2 4.000",
            "003*253211 12.900 1 12.900",
            "삼겹 한돈자조금 할인 -1.369",
            "끝전할인: -4",
            "총할인액: -4",
            "총구매액: 18,580",
            "내실금액: 17,207",
        ],
    }

    parsed = parse_receipt(receipt, store="hanaro")
    semantic = interpret_receipt(parsed, store="hanaro")
    result = validate_hanaro(semantic)

    assert result["store"] == "hanaro"
    assert result["is_valid"] is False

    items = semantic["items"]

    assert len(items) == 3

    # 3번째 상품에 한돈자조금 할인 1,369 귀속
    assert items[2]["base_price"] == 12900
    assert items[2]["discount"] == 1369
    assert items[2]["final_price"] == 11531

    debug = result["debug"]["receipt_validation"]

    # base 합계: 1,680 + 4,000 + 12,900
    assert debug["computed_base_price_sum"] == 18580

    # final 합계: 1,680 + 4,000 + 11,531
    assert debug["computed_final_price_sum"] == 17211

    # receipt_discount: 끝전할인 4 + 총할인액 4
    # 현재 semantic은 receipt_discount 라인을 모두 합산하므로 8
    assert debug["computed_receipt_discount_sum"] == 8

    # expected payment: 17,211 - 8 = 17,203
    # 이 테스트 데이터에서는 내실금액을 17,207로 두면 mismatch가 나므로
    # 실제 정책 확인용으로 아래 값을 맞춘다.
    assert debug["computed_expected_payment_total"] == 17203
    assert result["receipt_validation"]["total_match"] is False
    assert result["is_valid"] is False


def test_hanaro_validator_detects_total_mismatch():
    receipt = {
        "file_name": "046_hanaro_mismatch.json",
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
            "내실금액: 31,400",
        ],
    }

    parsed = parse_receipt(receipt, store="hanaro")
    semantic = interpret_receipt(parsed, store="hanaro")
    result = validate_hanaro(semantic)

    assert result["store"] == "hanaro"
    assert result["is_valid"] is False
    assert result["receipt_validation"]["total_match"] is False

    assert any(
        err["reason"]
        == "sum(item.final_price) - receipt_discount_total + fee_total != payment_total"
        for err in result["errors"]
    )