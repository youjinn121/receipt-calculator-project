from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: Optional[List[str]] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not fieldnames:
        keys = []
        seen = set()
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    keys.append(key)
                    seen.add(key)
        fieldnames = keys

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _stringify_for_csv(row.get(k)) for k in fieldnames})


def _stringify_for_csv(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value


def iter_json_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.json") if p.is_file())


def normalize_store(value: Any) -> str:
    return str(value or "").strip().lower()


def basename(value: Any) -> str:
    return Path(str(value or "")).name


def find_receipt_file(root: Path, store: str, receipt_file: str) -> Optional[Path]:
    """
    우선 data/<stage>/<store>/<receipt_file>을 찾고,
    없으면 root 전체에서 파일명 기준으로 검색한다.
    """
    receipt_file = basename(receipt_file)
    store = normalize_store(store)

    candidates = []
    if store:
        candidates.append(root / store / receipt_file)
    candidates.append(root / receipt_file)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    if root.exists():
        matches = sorted(root.rglob(receipt_file))
        if matches:
            return matches[0]

    return None


def load_ground_truths(gt_root: Path, stores: Optional[List[str]] = None) -> List[Tuple[Path, Dict[str, Any]]]:
    store_set = {normalize_store(s) for s in stores} if stores else None
    result = []
    for path in iter_json_files(gt_root):
        data = load_json(path)
        store = normalize_store(data.get("store") or path.parent.name)
        if store_set and store not in store_set:
            continue
        result.append((path, data))
    return result


def get_items(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = data.get("items", [])
    return items if isinstance(items, list) else []


def safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value).replace(",", "").strip())
    except Exception:
        return None


def rate(numerator: int, denominator: int) -> Optional[float]:
    if denominator == 0:
        return None
    return round(numerator / denominator * 100, 1)


def percent_str(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{value:.1f}%"


def group_sum(rows: Iterable[Dict[str, Any]], group_key: str) -> Dict[str, Counter]:
    grouped: Dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        key = str(row.get(group_key) or "unknown")
        for k, v in row.items():
            if isinstance(v, int):
                grouped[key][k] += v
    return grouped
