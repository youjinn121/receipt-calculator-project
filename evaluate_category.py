# evaluate_category.py

import json
from pathlib import Path
from collections import Counter, defaultdict

CATEGORIZED_ROOT = Path("data/categorized")
GT_ROOT = Path("data/ground_truth")

STORES = ["costco", "emart", "hanaro"]

# categorized 쪽에서 카테고리 필드명이 다를 수 있어서 후보를 넓게 잡음
PRED_CATEGORY_KEYS = [
    "category",
    "pred_category",
    "predicted_category",
    "llm_category",
    "primary_category",
]

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def get_pred_category(item: dict):
    for key in PRED_CATEGORY_KEYS:
        if key in item and item[key]:
            return item[key]
    return None

def normalize_name(name: str):
    return " ".join(str(name or "").strip().split())

def build_pred_map(categorized_data: dict):
    """
    categorized JSON의 items를 item_name/name 기준으로 매핑
    """
    result = {}

    for item in categorized_data.get("items", []):
        name = item.get("item_name") or item.get("name")
        pred = get_pred_category(item)

        if not name:
            continue

        result[normalize_name(name)] = {
            "item_name": name,
            "pred_category": pred,
            "raw": item,
        }

    return result

def evaluate_store(store: str):
    gt_dir = GT_ROOT / store
    pred_dir = CATEGORIZED_ROOT / store

    if not gt_dir.exists():
        print(f"[SKIP] GT 폴더 없음: {gt_dir}")
        return []

    if not pred_dir.exists():
        print(f"[SKIP] categorized 폴더 없음: {pred_dir}")
        return []

    rows = []

    for gt_path in sorted(gt_dir.glob("*_gt.json")):
        gt_data = load_json(gt_path)

        receipt_file = gt_data.get("receipt_file")
        if not receipt_file:
            print(f"[WARN] receipt_file 없음: {gt_path}")
            continue

        pred_path = pred_dir / receipt_file
        if not pred_path.exists():
            print(f"[MISS] 예측 파일 없음: {pred_path}")
            continue

        pred_data = load_json(pred_path)
        pred_map = build_pred_map(pred_data)

        for gt_item in gt_data.get("items", []):
            item_name = gt_item.get("item_name")
            gt_category = gt_item.get("gt_category")
            allowed = gt_item.get("allowed_categories") or [gt_category]
            confidence = gt_item.get("label_confidence")

            key = normalize_name(item_name)
            pred_item = pred_map.get(key)
            pred_category = pred_item["pred_category"] if pred_item else None
            if pred_item is None:
                debug_missing_item(
                    receipt_file=receipt_file,
                    gt_item_name=item_name,
                    pred_data=pred_data,
                )
            exact_match = pred_category == gt_category
            allowed_match = pred_category in allowed if pred_category else False

            rows.append({
                "store": store,
                "receipt_file": receipt_file,
                "item_name": item_name,
                "gt_category": gt_category,
                "pred_category": pred_category,
                "label_confidence": confidence,
                "allowed_categories": allowed,
                "exact_match": exact_match,
                "allowed_match": allowed_match,
                "missing_pred": pred_item is None,
            })

    return rows

def print_summary(rows):
    total = len(rows)
    if total == 0:
        print("비교할 항목이 없음")
        return

    exact_correct = sum(r["exact_match"] for r in rows)
    allowed_correct = sum(r["allowed_match"] for r in rows)
    missing = sum(r["missing_pred"] for r in rows)
    uncategorized = sum(r["pred_category"] == "Uncategorized" for r in rows)

    print("\n========== 전체 평가 ==========")
    print(f"총 GT item 수: {total:,}")
    print(f"정확 일치: {exact_correct:,} / {total:,} = {exact_correct / total * 100:.2f}%")
    print(f"허용 범위 일치: {allowed_correct:,} / {total:,} = {allowed_correct / total * 100:.2f}%")
    print(f"예측 누락: {missing:,}")
    print(f"Uncategorized 예측: {uncategorized:,} / {total:,} = {uncategorized / total * 100:.2f}%")

    by_store = defaultdict(list)
    for r in rows:
        by_store[r["store"]].append(r)

    print("\n========== 스토어별 평가 ==========")
    for store, store_rows in by_store.items():
        n = len(store_rows)
        e = sum(r["exact_match"] for r in store_rows)
        a = sum(r["allowed_match"] for r in store_rows)
        u = sum(r["pred_category"] == "Uncategorized" for r in store_rows)
        print(
            f"{store}: "
            f"items={n:,}, "
            f"exact={e / n * 100:.2f}%, "
            f"allowed={a / n * 100:.2f}%, "
            f"uncategorized={u / n * 100:.2f}%"
        )

    print("\n========== 카테고리별 정확 일치 ==========")
    by_gt = defaultdict(list)
    for r in rows:
        by_gt[r["gt_category"]].append(r)

    for cat, cat_rows in sorted(by_gt.items()):
        n = len(cat_rows)
        e = sum(r["exact_match"] for r in cat_rows)
        a = sum(r["allowed_match"] for r in cat_rows)
        print(f"{cat}: items={n:,}, exact={e / n * 100:.2f}%, allowed={a / n * 100:.2f}%")

def print_errors(rows):
    exact_errors = [r for r in rows if not r["exact_match"]]
    allowed_errors = [r for r in rows if not r["allowed_match"]]

    print("\n========== 확실한 오분류 allowed 밖 ==========")
    if not allowed_errors:
        print("없음")
    else:
        for r in allowed_errors:
            print(
                f"- {r['receipt_file']} | {r['item_name']} | "
                f"GT={r['gt_category']} | PRED={r['pred_category']} | "
                f"allowed={r['allowed_categories']}"
            )

    print("\n========== GT와 정확히 다르지만 allowed 안에는 들어간 애매 케이스 ==========")
    ambiguous = [r for r in exact_errors if r["allowed_match"]]
    if not ambiguous:
        print("없음")
    else:
        for r in ambiguous:
            print(
                f"- {r['receipt_file']} | {r['item_name']} | "
                f"GT={r['gt_category']} | PRED={r['pred_category']} | "
                f"allowed={r['allowed_categories']}"
            )

def debug_missing_item(receipt_file, gt_item_name, pred_data):
    print(f"\n[MISSING ITEM] {receipt_file}")
    print(f"GT item_name: {gt_item_name}")
    print("categorized item names:")

    for item in pred_data.get("items", []):
        name = item.get("item_name") or item.get("name")
        category = get_pred_category(item)
        print(f"  - {name} | pred={category}")

def main():
    all_rows = []

    for store in STORES:
        rows = evaluate_store(store)
        all_rows.extend(rows)

    print_summary(all_rows)
    print_errors(all_rows)

    # 결과 저장
    out_path = Path("category_eval_result.json")
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(all_rows, f, ensure_ascii=False, indent=2)

    print(f"\n상세 결과 저장 완료: {out_path}")

if __name__ == "__main__":
    main()