"""
[LLM Category Metrics]

카테고리 정규화 및 소비 분석 결과 품질 지표 생성 모듈.

평가 항목:
1. Category Coverage
   - 전체 상품 중 Uncategorized가 아닌 비율

2. Category Accuracy
   - 정답 라벨이 있는 경우, Uncategorized를 제외한 분류 정확도

3. Method Usage
   - fallback / llm / disabled 사용 비율

4. Category Distribution
   - 카테고리별 개수/금액 분포

5. Consumption Metrics
   - 길티 플레저 지수
   - 집밥 자립도
   - 생활 소비 비중
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from llm.category_schema import PRIMARY_CATEGORIES


GUILTY_PLEASURE_CATEGORIES = {"간식", "주류"}
HOME_COOKING_NUMERATOR = {"식재료"}
HOME_COOKING_DENOMINATOR = {"식재료", "간편식"}
LIFESTYLE_CATEGORIES = {"생활용품", "반려동물"}


def build_category_metrics(categorized_receipt: Dict[str, Any]) -> Dict[str, Any]:
    items = categorized_receipt.get("items", [])
    store = categorized_receipt.get("store")
    file_name = categorized_receipt.get("file_name")

    total_items = len(items)
    categorized_items = 0
    uncategorized_items = 0

    correct_items = 0
    evaluated_items = 0

    method_counts = {
            "fallback": 0,
            "llm": 0,
            "cache": 0,
            "disabled": 0,
            "unknown": 0,
    }

    category_counts = _init_category_count_map()
    category_amounts = _init_category_amount_map()

    total_final_price = 0

    for item in items:
        category = _normalize_metric_category(item.get("category"))
        final_price = _safe_int(item.get("final_price")) or 0
        total_final_price += final_price

        category_counts[category] += 1
        category_amounts[category] += final_price

        if category == "Uncategorized":
            uncategorized_items += 1
        else:
            categorized_items += 1

        gold_category = item.get("gold_category")
        if gold_category is not None and category != "Uncategorized":
            evaluated_items += 1
            if category == _normalize_metric_category(gold_category):
                correct_items += 1

        method = _extract_method(item)
        if method not in method_counts:
            method = "unknown"
        method_counts[method] += 1

    return {
        "file_name": file_name,
        "store": store,

        "total_items": total_items,
        "categorized_items": categorized_items,
        "uncategorized_items": uncategorized_items,

        "coverage_rate": _rate(categorized_items, total_items),
        "uncategorized_rate": _rate(uncategorized_items, total_items),

        # gold_category가 있는 경우에만 의미 있음
        "evaluated_items": evaluated_items,
        "correct_items": correct_items,
        "accuracy": _rate(correct_items, evaluated_items),

        "method_counts": method_counts,
        "method_rates": {
            key: _rate(value, total_items)
            for key, value in method_counts.items()
        },

        "category_counts": category_counts,
        "category_amounts": category_amounts,
        "category_amount_rates": {
            category: _rate(amount, total_final_price)
            for category, amount in category_amounts.items()
        },

        "total_final_price": total_final_price,

        "consumption_metrics": build_consumption_metrics_from_amounts(
            category_amounts=category_amounts,
            total_final_price=total_final_price,
        ),
    }


def build_category_metrics_for_many(
    categorized_receipts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    total_items = 0
    categorized_items = 0
    uncategorized_items = 0
    evaluated_items = 0
    correct_items = 0
    total_final_price = 0

    method_counts = {
            "fallback": 0,
            "llm": 0,
            "cache": 0,
            "disabled": 0,
            "unknown": 0,
    }

    category_counts = _init_category_count_map()
    category_amounts = _init_category_amount_map()
    store_counts: Dict[str, int] = {}
    store_success: Dict[str, Dict[str, int]] = {}

    receipt_metric_list: List[Dict[str, Any]] = []

    for receipt in categorized_receipts:
        receipt_metrics = build_category_metrics(receipt)
        receipt_metric_list.append(receipt_metrics)

        store = str(receipt_metrics.get("store") or "unknown")
        store_counts[store] = store_counts.get(store, 0) + 1

        total_items += receipt_metrics["total_items"]
        categorized_items += receipt_metrics["categorized_items"]
        uncategorized_items += receipt_metrics["uncategorized_items"]
        evaluated_items += receipt_metrics["evaluated_items"]
        correct_items += receipt_metrics["correct_items"]
        total_final_price += receipt_metrics["total_final_price"]

        for key, value in receipt_metrics["method_counts"].items():
            method_counts[key] = method_counts.get(key, 0) + value

        for category, count in receipt_metrics["category_counts"].items():
            category_counts[category] += count

        for category, amount in receipt_metrics["category_amounts"].items():
            category_amounts[category] += amount

        if store not in store_success:
            store_success[store] = {
                "total_items": 0,
                "categorized_items": 0,
                "uncategorized_items": 0,
                "evaluated_items": 0,
                "correct_items": 0,
            }

        store_success[store]["total_items"] += receipt_metrics["total_items"]
        store_success[store]["categorized_items"] += receipt_metrics["categorized_items"]
        store_success[store]["uncategorized_items"] += receipt_metrics["uncategorized_items"]
        store_success[store]["evaluated_items"] += receipt_metrics["evaluated_items"]
        store_success[store]["correct_items"] += receipt_metrics["correct_items"]

    return {
        "receipt_count": len(categorized_receipts),
        "store_counts": store_counts,

        "total_items": total_items,
        "categorized_items": categorized_items,
        "uncategorized_items": uncategorized_items,

        "coverage_rate": _rate(categorized_items, total_items),
        "uncategorized_rate": _rate(uncategorized_items, total_items),

        "evaluated_items": evaluated_items,
        "correct_items": correct_items,
        "accuracy": _rate(correct_items, evaluated_items),

        "method_counts": method_counts,
        "method_rates": {
            key: _rate(value, total_items)
            for key, value in method_counts.items()
        },

        "category_counts": category_counts,
        "category_amounts": category_amounts,
        "category_amount_rates": {
            category: _rate(amount, total_final_price)
            for category, amount in category_amounts.items()
        },

        "store_success_rates": {
            store: {
                **values,
                "coverage_rate": _rate(values["categorized_items"], values["total_items"]),
                "uncategorized_rate": _rate(values["uncategorized_items"], values["total_items"]),
                "accuracy": _rate(values["correct_items"], values["evaluated_items"]),
            }
            for store, values in store_success.items()
        },

        "total_final_price": total_final_price,

        "consumption_metrics": build_consumption_metrics_from_amounts(
            category_amounts=category_amounts,
            total_final_price=total_final_price,
        ),

        "receipt_metrics": receipt_metric_list,
    }


def build_consumption_metrics_from_amounts(
    category_amounts: Dict[str, int],
    total_final_price: int,
) -> Dict[str, Any]:
    guilty_amount = _sum_amounts(category_amounts, GUILTY_PLEASURE_CATEGORIES)
    home_food_amount = _sum_amounts(category_amounts, HOME_COOKING_NUMERATOR)
    home_food_base = _sum_amounts(category_amounts, HOME_COOKING_DENOMINATOR)
    lifestyle_amount = _sum_amounts(category_amounts, LIFESTYLE_CATEGORIES)

    return {
        "guilty_pleasure_index": _rate(guilty_amount, total_final_price),
        "home_cooking_independence": _rate(home_food_amount, home_food_base),
        "lifestyle_consumption_rate": _rate(lifestyle_amount, total_final_price),

        "raw_values": {
            "guilty_pleasure_amount": guilty_amount,
            "home_food_amount": home_food_amount,
            "home_food_base_amount": home_food_base,
            "lifestyle_amount": lifestyle_amount,
            "total_final_price": total_final_price,
        },
    }


def compare_consumption_metrics(
    predicted_metrics: Dict[str, Any],
    gold_metrics: Dict[str, Any],
    tolerance: float = 0.01,
) -> Dict[str, Any]:
    """
    시스템 계산 지표와 사람이 직접 계산한 정답 지표를 비교한다.

    tolerance:
        퍼센트 단위 허용 오차.
        예: 0.01이면 0.01%p 차이까지 일치로 인정.
    """

    metric_names = [
        "guilty_pleasure_index",
        "home_cooking_independence",
        "lifestyle_consumption_rate",
    ]

    results: Dict[str, Any] = {}
    match_count = 0
    compared_count = 0

    for name in metric_names:
        pred = _safe_float(predicted_metrics.get(name))
        gold = _safe_float(gold_metrics.get(name))

        if pred is None or gold is None:
            results[name] = {
                "predicted": pred,
                "gold": gold,
                "match": None,
                "diff": None,
            }
            continue

        diff = round(abs(pred - gold), 4)
        match = diff <= tolerance

        compared_count += 1
        if match:
            match_count += 1

        results[name] = {
            "predicted": pred,
            "gold": gold,
            "match": match,
            "diff": diff,
        }

    return {
        "compared_count": compared_count,
        "match_count": match_count,
        "metric_match_rate": _rate(match_count, compared_count),
        "details": results,
    }


def attach_category_metrics(
    categorized_receipt: Dict[str, Any],
) -> Dict[str, Any]:
    result = dict(categorized_receipt)
    result["category_metrics"] = build_category_metrics(categorized_receipt)
    return result


def _init_category_count_map() -> Dict[str, int]:
    return {category: 0 for category in PRIMARY_CATEGORIES}


def _init_category_amount_map() -> Dict[str, int]:
    return {category: 0 for category in PRIMARY_CATEGORIES}


def _normalize_metric_category(category: Any) -> str:
    text = str(category or "").strip()

    if text in PRIMARY_CATEGORIES:
        return text

    return "Uncategorized"


def _extract_method(item: Dict[str, Any]) -> str:
    meta = item.get("category_meta", {})

    if not isinstance(meta, dict):
        return "unknown"

    method = str(meta.get("method") or "").strip()

    if not method:
        return "unknown"

    return method


def _sum_amounts(
    category_amounts: Dict[str, int],
    categories: set[str],
) -> int:
    total = 0

    for category in categories:
        total += _safe_int(category_amounts.get(category)) or 0

    return total


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0

    return round((numerator / denominator) * 100, 2)


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None

    try:
        return int(value)
    except Exception:
        return None


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None

    try:
        return float(value)
    except Exception:
        return None