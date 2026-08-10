from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from evaluation.eval_utils import iter_json_files, load_json, normalize_store, rate, save_json, write_csv


def evaluate_validation(validation_root: Path, out_dir: Path, stores: Optional[List[str]]) -> None:
    store_filter = {normalize_store(s) for s in stores} if stores else None
    receipt_rows: List[Dict[str, Any]] = []
    reason_rows: List[Dict[str, Any]] = []

    for path in iter_json_files(validation_root):
        data = load_json(path)
        store = normalize_store(data.get("store") or path.parent.name)
        if store_filter and store not in store_filter:
            continue

        item_val = data.get("item_validation", {}) or {}
        receipt_val = data.get("receipt_validation", {}) or {}
        debug_receipt = ((data.get("debug", {}) or {}).get("receipt_validation", {}) or {})
        reasons = data.get("recapture_reasons", []) or []

        row = {
            "receipt_file": data.get("file_name") or path.name,
            "store": store,
            "is_valid": bool(data.get("is_valid")),
            "checked_item_count": int(item_val.get("checked_item_count") or 0),
            "valid_item_count": int(item_val.get("valid_item_count") or 0),
            "invalid_item_count": int(item_val.get("invalid_item_count") or 0),
            "total_match": receipt_val.get("total_match"),
            "subtotal_segment_match": receipt_val.get("subtotal_segment_match"),
            "is_total_inferred": bool(data.get("is_total_inferred")),
            "requires_user_total_confirmation": bool(data.get("requires_user_total_confirmation")),
            "recapture_recommended": bool(data.get("recapture_recommended")),
            "recapture_reasons": reasons,
            "computed_final_price_sum": debug_receipt.get("computed_final_price_sum"),
            "receipt_total": debug_receipt.get("receipt_total") or debug_receipt.get("payment_total"),
            "receipt_total_source": debug_receipt.get("receipt_total_source"),
        }
        receipt_rows.append(row)

        for reason in reasons:
            reason_rows.append({
                "receipt_file": row["receipt_file"],
                "store": store,
                "reason": reason,
            })

    summary_rows = build_summary_rows(receipt_rows)
    reason_summary_rows = build_reason_summary_rows(reason_rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "validation_receipt_detail.csv", receipt_rows)
    write_csv(out_dir / "validation_summary.csv", summary_rows)
    write_csv(out_dir / "validation_recapture_reason_counts.csv", reason_summary_rows)
    save_json(out_dir / "validation_summary.json", summary_rows)

    print("[OK] Validation evaluation completed")
    print(f"- receipt detail: {out_dir / 'validation_receipt_detail.csv'}")
    print(f"- summary       : {out_dir / 'validation_summary.csv'}")
    print(f"- reasons       : {out_dir / 'validation_recapture_reason_counts.csv'}")


def build_summary_rows(receipt_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in receipt_rows:
        grouped[row["store"]].append(row)
    grouped["ALL"] = receipt_rows

    result = []
    for store, rows in grouped.items():
        receipt_total = len(rows)
        valid_count = sum(1 for r in rows if r["is_valid"])
        invalid_count = receipt_total - valid_count
        checked_items = sum(int(r["checked_item_count"] or 0) for r in rows)
        valid_items = sum(int(r["valid_item_count"] or 0) for r in rows)
        invalid_items = sum(int(r["invalid_item_count"] or 0) for r in rows)

        total_match_true = sum(1 for r in rows if r["total_match"] is True)
        total_match_false = sum(1 for r in rows if r["total_match"] is False)
        total_match_none = receipt_total - total_match_true - total_match_false
        known_total = total_match_true + total_match_false

        result.append({
            "store": store,
            "receipt_total": receipt_total,
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "validation_pass_rate": rate(valid_count, receipt_total),
            "checked_item_count": checked_items,
            "valid_item_count": valid_items,
            "invalid_item_count": invalid_items,
            "item_validation_success_rate": rate(valid_items, checked_items),
            "total_match_true": total_match_true,
            "total_match_false": total_match_false,
            "total_match_none": total_match_none,
            "total_match_rate_all_receipts": rate(total_match_true, receipt_total),
            "total_match_rate_known_only": rate(total_match_true, known_total),
            "inferred_total_count": sum(1 for r in rows if r["is_total_inferred"]),
            "recapture_recommended_count": sum(1 for r in rows if r["recapture_recommended"]),
        })
    return result


def build_reason_summary_rows(reason_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counter = Counter((r["store"], r["reason"]) for r in reason_rows)
    result = [
        {"store": store, "reason": reason, "count": count}
        for (store, reason), count in sorted(counter.items())
    ]
    total_counter = Counter(r["reason"] for r in reason_rows)
    result.extend(
        {"store": "ALL", "reason": reason, "count": count}
        for reason, count in sorted(total_counter.items())
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate validation outputs.")
    parser.add_argument("--validation-root", default="data/validation")
    parser.add_argument("--out-dir", default="evaluation/results")
    parser.add_argument("--stores", nargs="*", default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    evaluate_validation(
        validation_root=Path(args.validation_root),
        out_dir=Path(args.out_dir),
        stores=args.stores,
    )
