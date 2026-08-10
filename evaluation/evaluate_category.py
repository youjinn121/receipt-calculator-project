from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from evaluation.eval_utils import (
    basename,
    find_receipt_file,
    get_items,
    load_ground_truths,
    load_json,
    normalize_store,
    rate,
    save_json,
    write_csv,
)

UNCATEGORIZED = "Uncategorized"


def extract_pred_category(item: Optional[Dict[str, Any]]) -> Optional[str]:
    if not item:
        return None

    direct_keys = [
        "category",
        "pred_category",
        "llm_category",
        "final_category",
        "normalized_category",
    ]
    for key in direct_keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    nested_candidates = [
        item.get("category_result"),
        item.get("category_meta"),
        item.get("llm_result"),
    ]
    for nested in nested_candidates:
        if isinstance(nested, dict):
            for key in direct_keys:
                value = nested.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

    return None


def is_category_eval_target(gt_item: Dict[str, Any]) -> bool:
    if gt_item.get("exclude_from_category_eval") is True:
        return False
    if str(gt_item.get("label_confidence") or "").lower() == "invalid":
        return False
    if gt_item.get("gt_category") is None:
        return False
    return True


def get_allowed_categories(gt_item: Dict[str, Any]) -> List[str]:
    gt_category = gt_item.get("gt_category")
    allowed = gt_item.get("allowed_categories") or []
    if not isinstance(allowed, list):
        allowed = []
    allowed = [str(x).strip() for x in allowed if str(x).strip()]
    if gt_category and gt_category not in allowed:
        allowed.append(str(gt_category))
    return allowed


def classify_status(pred_category: Optional[str], gt_category: str, allowed: List[str]) -> str:
    if pred_category is None:
        return "missing_pred"
    if pred_category == UNCATEGORIZED:
        return "uncategorized"
    if pred_category == gt_category:
        return "strict_correct"
    if pred_category in allowed:
        return "allowed_mismatch"
    return "real_mismatch"


def evaluate_category(gt_root: Path, categorized_root: Path, out_dir: Path, stores: Optional[List[str]]) -> None:
    gt_docs = load_ground_truths(gt_root, stores=stores)
    rows: List[Dict[str, Any]] = []

    for gt_path, gt in gt_docs:
        store = normalize_store(gt.get("store") or gt_path.parent.name)
        receipt_file = basename(gt.get("receipt_file") or gt_path.name)
        gt_items = get_items(gt)

        pred_path = find_receipt_file(categorized_root, store, receipt_file)
        pred_doc = load_json(pred_path) if pred_path else None
        pred_items = get_items(pred_doc) if pred_doc else []

        for idx, gt_item in enumerate(gt_items):
            if not is_category_eval_target(gt_item):
                continue

            item_order = int(gt_item.get("item_order") or idx + 1)
            pred_item = pred_items[item_order - 1] if item_order - 1 < len(pred_items) else None
            pred_category = extract_pred_category(pred_item)
            gt_category = str(gt_item.get("gt_category"))
            allowed = get_allowed_categories(gt_item)
            status = classify_status(pred_category, gt_category, allowed)

            rows.append({
                "receipt_file": receipt_file,
                "store": store,
                "item_order": item_order,
                "gt_name": gt_item.get("gt_name"),
                "pred_name": pred_item.get("name") if pred_item else None,
                "gt_category": gt_category,
                "pred_category": pred_category,
                "label_confidence": gt_item.get("label_confidence"),
                "allowed_categories": allowed,
                "strict_match": status == "strict_correct",
                "allowed_match": status in {"strict_correct", "allowed_mismatch"},
                "is_uncategorized": pred_category == UNCATEGORIZED,
                "status": status,
                "basis": gt_item.get("basis"),
                "reason": gt_item.get("reason"),
                "categorized_file_exists": pred_path is not None,
                "categorized_path": str(pred_path) if pred_path else None,
            })

    summary_rows = build_summary_rows(rows)
    confidence_rows = build_confidence_rows(rows)
    confusion_rows = build_confusion_rows(rows)

    allowed_mismatch_rows = [r for r in rows if r["status"] == "allowed_mismatch"]
    real_mismatch_rows = [r for r in rows if r["status"] == "real_mismatch"]
    uncategorized_rows = [r for r in rows if r["status"] == "uncategorized"]
    missing_pred_rows = [r for r in rows if r["status"] == "missing_pred"]

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "category_item_detail.csv", rows)
    write_csv(out_dir / "category_summary.csv", summary_rows)
    write_csv(out_dir / "category_by_label_confidence.csv", confidence_rows)
    write_csv(out_dir / "category_confusion.csv", confusion_rows)
    write_csv(out_dir / "category_allowed_mismatches.csv", allowed_mismatch_rows)
    write_csv(out_dir / "category_real_mismatches.csv", real_mismatch_rows)
    write_csv(out_dir / "category_uncategorized.csv", uncategorized_rows)
    write_csv(out_dir / "category_missing_pred.csv", missing_pred_rows)
    save_json(out_dir / "category_summary.json", summary_rows)

    print("[OK] Category evaluation completed")
    print(f"- item detail       : {out_dir / 'category_item_detail.csv'}")
    print(f"- summary           : {out_dir / 'category_summary.csv'}")
    print(f"- allowed mismatches: {out_dir / 'category_allowed_mismatches.csv'}")
    print(f"- real mismatches   : {out_dir / 'category_real_mismatches.csv'}")


def build_summary_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["store"]].append(row)
    grouped["ALL"] = rows

    result = []
    for store, group in grouped.items():
        total = len(group)
        strict_correct = sum(1 for r in group if r["strict_match"])
        allowed_correct = sum(1 for r in group if r["allowed_match"])
        uncategorized = sum(1 for r in group if r["status"] == "uncategorized")
        missing_pred = sum(1 for r in group if r["status"] == "missing_pred")
        allowed_mismatch = sum(1 for r in group if r["status"] == "allowed_mismatch")
        real_mismatch = sum(1 for r in group if r["status"] == "real_mismatch")

        result.append({
            "store": store,
            "evaluated_item_count": total,
            "strict_correct_count": strict_correct,
            "strict_accuracy": rate(strict_correct, total),
            "allowed_correct_count": allowed_correct,
            "allowed_accuracy": rate(allowed_correct, total),
            "uncategorized_count": uncategorized,
            "uncategorized_rate": rate(uncategorized, total),
            "missing_pred_count": missing_pred,
            "allowed_mismatch_count": allowed_mismatch,
            "real_mismatch_count": real_mismatch,
            "effective_error_count": uncategorized + missing_pred + real_mismatch,
            "effective_error_rate": rate(uncategorized + missing_pred + real_mismatch, total),
        })
    return result


def build_confidence_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["store"], row.get("label_confidence") or "unknown")].append(row)
    # 전체도 추가
    for row in rows:
        grouped[("ALL", row.get("label_confidence") or "unknown")].append(row)

    result = []
    for (store, confidence), group in sorted(grouped.items()):
        total = len(group)
        strict_correct = sum(1 for r in group if r["strict_match"])
        allowed_correct = sum(1 for r in group if r["allowed_match"])
        result.append({
            "store": store,
            "label_confidence": confidence,
            "evaluated_item_count": total,
            "strict_correct_count": strict_correct,
            "strict_accuracy": rate(strict_correct, total),
            "allowed_correct_count": allowed_correct,
            "allowed_accuracy": rate(allowed_correct, total),
            "uncategorized_count": sum(1 for r in group if r["status"] == "uncategorized"),
            "real_mismatch_count": sum(1 for r in group if r["status"] == "real_mismatch"),
            "allowed_mismatch_count": sum(1 for r in group if r["status"] == "allowed_mismatch"),
        })
    return result


def build_confusion_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counter = Counter()
    for row in rows:
        if row["status"] in {"strict_correct", "allowed_mismatch"}:
            continue
        counter[(row["gt_category"], row.get("pred_category") or "MISSING", row["status"])] += 1

    return [
        {
            "gt_category": gt,
            "pred_category": pred,
            "status": status,
            "count": count,
        }
        for (gt, pred, status), count in sorted(counter.items())
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate categorized outputs against GT.")
    parser.add_argument("--gt-root", default="data/ground_truth")
    parser.add_argument("--categorized-root", default="data/categorized")
    parser.add_argument("--out-dir", default="evaluation/results")
    parser.add_argument("--stores", nargs="*", default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    evaluate_category(
        gt_root=Path(args.gt_root),
        categorized_root=Path(args.categorized_root),
        out_dir=Path(args.out_dir),
        stores=args.stores,
    )
