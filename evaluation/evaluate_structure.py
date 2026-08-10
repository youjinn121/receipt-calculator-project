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
    safe_int,
    write_csv,
)

DEFAULT_REQUIRED_FIELDS = [
    "name",
    "qty",
    "unit_price",
    "base_price",
    "discount",
    "final_price",
]


def has_required_fields(item: Dict[str, Any], required_fields: List[str]) -> bool:
    for field in required_fields:
        value = item.get(field)
        if value is None:
            return False
        if field == "name" and str(value).strip() == "":
            return False
    return True


def compare_core_fields(gt_item: Dict[str, Any], pred_item: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if pred_item is None:
        return {
            "core_match": False,
            "qty_match": False,
            "final_price_match": False,
            "base_price_match": False,
            "discount_match": False,
            "unit_price_match": False,
        }

    checks = {
        "qty_match": safe_int(pred_item.get("qty")) == safe_int(gt_item.get("gt_qty")),
        "unit_price_match": safe_int(pred_item.get("unit_price")) == safe_int(gt_item.get("gt_unit_price")),
        "base_price_match": safe_int(pred_item.get("base_price")) == safe_int(gt_item.get("gt_base_price")),
        "discount_match": safe_int(pred_item.get("discount")) == safe_int(gt_item.get("gt_discount")),
        "final_price_match": safe_int(pred_item.get("final_price")) == safe_int(gt_item.get("gt_final_price")),
    }
    # 상품 단위 구조화 핵심 평가는 수량 + 최종 상품 금액 중심
    checks["core_match"] = bool(checks["qty_match"] and checks["final_price_match"])
    return checks


def evaluate_structure(gt_root: Path, semantic_root: Path, out_dir: Path, stores: Optional[List[str]]) -> None:
    gt_docs = load_ground_truths(gt_root, stores=stores)
    required_fields = DEFAULT_REQUIRED_FIELDS

    receipt_rows: List[Dict[str, Any]] = []
    item_rows: List[Dict[str, Any]] = []

    for gt_path, gt in gt_docs:
        store = normalize_store(gt.get("store") or gt_path.parent.name)
        receipt_file = basename(gt.get("receipt_file") or gt_path.name)
        gt_items = get_items(gt)

        semantic_path = find_receipt_file(semantic_root, store, receipt_file)
        semantic = load_json(semantic_path) if semantic_path else None
        pred_items = get_items(semantic) if semantic else []

        generated_item_count = len(pred_items)
        gt_item_count = len(gt_items)
        semantic_file_exists = semantic_path is not None
        items_generated_success = semantic_file_exists and generated_item_count > 0

        complete_item_count = sum(1 for item in pred_items if has_required_fields(item, required_fields))

        core_match_count = 0
        qty_match_count = 0
        final_price_match_count = 0

        for idx, gt_item in enumerate(gt_items):
            pred_item = pred_items[idx] if idx < len(pred_items) else None
            checks = compare_core_fields(gt_item, pred_item)
            if checks["core_match"]:
                core_match_count += 1
            if checks["qty_match"]:
                qty_match_count += 1
            if checks["final_price_match"]:
                final_price_match_count += 1

            item_rows.append({
                "receipt_file": receipt_file,
                "store": store,
                "item_order": gt_item.get("item_order", idx + 1),
                "gt_name": gt_item.get("gt_name"),
                "pred_name": pred_item.get("name") if pred_item else None,
                "gt_qty": gt_item.get("gt_qty"),
                "pred_qty": pred_item.get("qty") if pred_item else None,
                "gt_unit_price": gt_item.get("gt_unit_price"),
                "pred_unit_price": pred_item.get("unit_price") if pred_item else None,
                "gt_base_price": gt_item.get("gt_base_price"),
                "pred_base_price": pred_item.get("base_price") if pred_item else None,
                "gt_discount": gt_item.get("gt_discount"),
                "pred_discount": pred_item.get("discount") if pred_item else None,
                "gt_final_price": gt_item.get("gt_final_price"),
                "pred_final_price": pred_item.get("final_price") if pred_item else None,
                "missing_pred": pred_item is None,
                **checks,
            })

        receipt_rows.append({
            "receipt_file": receipt_file,
            "store": store,
            "semantic_file_exists": semantic_file_exists,
            "items_generated_success": items_generated_success,
            "gt_item_count": gt_item_count,
            "generated_item_count": generated_item_count,
            "item_count_match": generated_item_count == gt_item_count,
            "required_field_complete_item_count": complete_item_count,
            "required_field_incomplete_item_count": max(generated_item_count - complete_item_count, 0),
            "required_field_completion_rate": rate(complete_item_count, generated_item_count),
            "core_match_count": core_match_count,
            "core_match_rate_over_gt": rate(core_match_count, gt_item_count),
            "qty_match_count": qty_match_count,
            "qty_match_rate_over_gt": rate(qty_match_count, gt_item_count),
            "final_price_match_count": final_price_match_count,
            "final_price_match_rate_over_gt": rate(final_price_match_count, gt_item_count),
            "semantic_path": str(semantic_path) if semantic_path else None,
        })

    summary_rows = build_summary_rows(receipt_rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "structure_receipt_detail.csv", receipt_rows)
    write_csv(out_dir / "structure_item_detail.csv", item_rows)
    write_csv(out_dir / "structure_summary.csv", summary_rows)
    save_json(out_dir / "structure_summary.json", summary_rows)

    print("[OK] Structure evaluation completed")
    print(f"- receipt detail: {out_dir / 'structure_receipt_detail.csv'}")
    print(f"- item detail   : {out_dir / 'structure_item_detail.csv'}")
    print(f"- summary       : {out_dir / 'structure_summary.csv'}")


def build_summary_rows(receipt_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in receipt_rows:
        grouped[row["store"]].append(row)
    grouped["ALL"] = receipt_rows

    result = []
    for store, rows in grouped.items():
        receipt_total = len(rows)
        semantic_file_found = sum(1 for r in rows if r["semantic_file_exists"])
        items_success = sum(1 for r in rows if r["items_generated_success"])
        item_count_match = sum(1 for r in rows if r["item_count_match"])

        gt_item_total = sum(int(r["gt_item_count"] or 0) for r in rows)
        generated_item_total = sum(int(r["generated_item_count"] or 0) for r in rows)
        complete_item_total = sum(int(r["required_field_complete_item_count"] or 0) for r in rows)
        core_match_total = sum(int(r["core_match_count"] or 0) for r in rows)
        qty_match_total = sum(int(r["qty_match_count"] or 0) for r in rows)
        final_price_match_total = sum(int(r["final_price_match_count"] or 0) for r in rows)

        result.append({
            "store": store,
            "receipt_total": receipt_total,
            "semantic_file_found": semantic_file_found,
            "semantic_file_found_rate": rate(semantic_file_found, receipt_total),
            "items_generation_success_count": items_success,
            "items_generation_success_rate": rate(items_success, receipt_total),
            "item_count_match_count": item_count_match,
            "item_count_match_rate": rate(item_count_match, receipt_total),
            "gt_item_total": gt_item_total,
            "generated_item_total": generated_item_total,
            "required_field_complete_item_total": complete_item_total,
            "required_field_completion_rate": rate(complete_item_total, generated_item_total),
            "core_match_total": core_match_total,
            "core_match_rate_over_gt": rate(core_match_total, gt_item_total),
            "qty_match_total": qty_match_total,
            "qty_match_rate_over_gt": rate(qty_match_total, gt_item_total),
            "final_price_match_total": final_price_match_total,
            "final_price_match_rate_over_gt": rate(final_price_match_total, gt_item_total),
        })
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate semantic structure outputs against GT.")
    parser.add_argument("--gt-root", default="data/ground_truth")
    parser.add_argument("--semantic-root", default="data/semantic")
    parser.add_argument("--out-dir", default="evaluation/results")
    parser.add_argument("--stores", nargs="*", default=None, help="Optional store filters: costco emart hanaro")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    evaluate_structure(
        gt_root=Path(args.gt_root),
        semantic_root=Path(args.semantic_root),
        out_dir=Path(args.out_dir),
        stores=args.stores,
    )
