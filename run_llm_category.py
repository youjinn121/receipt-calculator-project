import json
import re
from pathlib import Path

from llm.category_manager import categorize_receipt_items


INPUT_ROOT = Path("data/semantic")
OUTPUT_ROOT = Path("data/categorized")

# 코드 수정 반영 확인 대상만 실행
TARGET_FILES = {
    "costco": [
        "004_costco.json",  # 오뚜기 순 후 추
        "020_costco.json",  # 워터보일드베이글
    ],
    "emart": [
        "035_emart.json",  # 스테비아, 슈가버블 문맥
        "044_emart.json",  # 드립백 확인
    ],
    "hanaro": [
        "053_hanaro.json",  # 빙그레요구르트
    ],
}
USE_CACHE = False
SAVE_CACHE = False


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def categorize_store(store: str, file_names: list[str]):
    input_dir = INPUT_ROOT / store
    output_dir = OUTPUT_ROOT / store

    if not input_dir.exists():
        print(f"[SKIP] {input_dir} 없음")
        return

    print(f"\n[{store}] {len(file_names)}개 처리 시작")

    for file_name in file_names:
        path = input_dir / file_name

        if not path.exists():
            print(f"[SKIP] {path} 없음")
            continue

        semantic = load_json(path)

        categorized = categorize_receipt_items(
            semantic_receipt=semantic,
            use_llm=True,
            use_fallback=False,
            use_cache=USE_CACHE,
            save_cache=SAVE_CACHE,
        )

        output_path = output_dir / path.name
        save_json(categorized, output_path)

        metrics = categorized.get("category_metrics", {})

        print(
            f"[OK] {path.name} "
            f"| items={metrics.get('total_items')} "
            f"| coverage={metrics.get('coverage_rate')}% "
            f"| uncategorized={metrics.get('uncategorized_items')}"
        )


def main():
    for store, file_names in TARGET_FILES.items():
        categorize_store(store, file_names)


if __name__ == "__main__":
    main()