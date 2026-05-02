import json
from pathlib import Path

from llm.category_manager import categorize_receipt_items


INPUT_ROOT = Path("data/semantic")
OUTPUT_ROOT = Path("data/categorized")

STORES = ["costco", "emart", "hanaro"]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def categorize_store(store: str, limit: int | None = None):
    input_dir = INPUT_ROOT / store
    output_dir = OUTPUT_ROOT / store

    if not input_dir.exists():
        print(f"[SKIP] {input_dir} 없음")
        return

    files = sorted(input_dir.glob("*.json"))

    if limit is not None:
        files = files[:limit]

    print(f"\n[{store}] {len(files)}개 처리 시작")

    for path in files:
        semantic = load_json(path)

        categorized = categorize_receipt_items(
            semantic_receipt=semantic,
            use_llm=True,
            use_fallback=False,  # 평가용: fallback 끔
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
    # 처음에는 과금 방지용으로 매장별 2개만
    for store in STORES:
        categorize_store(store, limit=2)


if __name__ == "__main__":
    main()