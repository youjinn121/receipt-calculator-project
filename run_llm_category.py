import json
import re
from pathlib import Path

from llm.category_manager import categorize_receipt_items


INPUT_ROOT = Path("data/semantic")
OUTPUT_ROOT = Path("data/categorized")
VALIDATION_ROOT = Path("data/validation")

USE_CACHE = False
SAVE_CACHE = False

# validation is_valid=True인 파일만 처리됨
TARGET_RANGES = {
    #"costco": (1, 37),
    #"hanaro": (38, 76),
    "emart": (77, 100),
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_validation_passed(store: str, file_name: str) -> bool:
    """
    data/validation/{store}/{file_name} 기준으로
    is_valid=True인 영수증만 LLM category 대상으로 사용한다.
    """

    validation_path = VALIDATION_ROOT / store / file_name

    if not validation_path.exists():
        print(f"[SKIP] {file_name} | validation 파일 없음")
        return False

    validation = load_json(validation_path)

    if validation.get("is_valid") is not True:
        print(f"[SKIP] {file_name} | is_valid=False")
        return False

    return True


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


def normalize_target_numbers(target_numbers) -> set[int] | None:
    """
    TARGET_RANGES 입력 형태 지원:
    - [67, 72]       -> 67, 72만 처리
    - (67, 72)       -> 67~72 범위 처리
    - None           -> 전체 처리
    """

    if target_numbers is None:
        return None

    if isinstance(target_numbers, tuple) and len(target_numbers) == 2:
        start, end = target_numbers
        return set(range(start, end + 1))

    return set(target_numbers)


def categorize_store(store: str, target_numbers=None):
    input_dir = INPUT_ROOT / store
    output_dir = OUTPUT_ROOT / store

    if not input_dir.exists():
        print(f"[SKIP] input dir 없음: {input_dir}")
        return

    target_number_set = normalize_target_numbers(target_numbers)

    files = sorted(input_dir.glob("*.json"))

    target_files = []

    for file_path in files:
        receipt_no = extract_receipt_no(file_path)

        if receipt_no is None:
            continue

        if target_number_set is None or receipt_no in target_number_set:
            target_files.append(file_path)

    print(f"\n[{store}] 후보 {len(target_files)}개 확인 시작")

    processed_count = 0
    skipped_count = 0

    for file_path in target_files:
        if not is_validation_passed(store, file_path.name):
            skipped_count += 1
            continue

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

        processed_count += 1

        print(
            f"[OK] {file_path.name} | "
            f"items={total_items} | "
            f"coverage={coverage}% | "
            f"uncategorized={uncategorized_count}"
        )

    print(
        f"[DONE] {store} | "
        f"processed={processed_count} | "
        f"skipped={skipped_count}"
    )


def main():
    for store, target_numbers in TARGET_RANGES.items():
        categorize_store(store, target_numbers)


if __name__ == "__main__":
    main()