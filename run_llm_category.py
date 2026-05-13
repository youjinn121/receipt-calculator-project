import json
import re
from pathlib import Path

from llm.category_manager import categorize_receipt_items


INPUT_ROOT = Path("data/semantic")
OUTPUT_ROOT = Path("data/categorized")

# 오분류 수정 반영 대상만 실행
TARGET_RANGES = {
    ##"costco": [24],
    "emart": [39],
    ##"hanaro": [47, 49, 61],
}

USE_CACHE = True
SAVE_CACHE = True


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_receipt_no(path: Path) -> int | None:
    """
    예:
    - 006_costco.json -> 6
    - 035_emart.json -> 35
    - 061_hanaro.json -> 61
    """

    match = re.match(r"^(\d+)_", path.name)

    if not match:
        return None

    return int(match.group(1))


def categorize_store(store: str, target_numbers: list[int]):
    input_dir = INPUT_ROOT / store
    output_dir = OUTPUT_ROOT / store

    if not input_dir.exists():
        print(f"[SKIP] input dir 없음: {input_dir}")
        return

    files = sorted(input_dir.glob("*.json"))

    target_files = []

    for file_path in files:
        receipt_no = extract_receipt_no(file_path)

        if receipt_no in target_numbers:
            target_files.append(file_path)

    print(f"\n[{store}] {len(target_files)}개 처리 시작")

    for file_path in target_files:
        semantic_receipt = load_json(file_path)

        categorized_receipt = categorize_receipt_items(
            semantic_receipt=semantic_receipt,
            use_cache=USE_CACHE,
            save_cache=SAVE_CACHE,
        )

        output_path = output_dir / file_path.name

        save_json(categorized_receipt, output_path)

        items = categorized_receipt.get("items", [])

        total_items = len(items)

        uncategorized_count = sum(
            1
            for item in items
            if item.get("category") in (None, "", "Uncategorized")
        )

        coverage = (
            0.0
            if total_items == 0
            else round(
                (total_items - uncategorized_count)
                / total_items
                * 100,
                1,
            )
        )

        print(
            f"[OK] {file_path.name} | "
            f"items={total_items} | "
            f"coverage={coverage}% | "
            f"uncategorized={uncategorized_count}"
        )


def main():
    for store, target_numbers in TARGET_RANGES.items():
        categorize_store(store, target_numbers)


if __name__ == "__main__":
    main()