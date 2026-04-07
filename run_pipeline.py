from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from receipt_parser.parser_pipeline import parse_receipt
from semantic import interpret_receipt
from validation.validator import validate_receipt


PROJECT_ROOT = Path(__file__).resolve().parent

RAW_ROOT = PROJECT_ROOT / "data" / "raw"
PARSED_ROOT = PROJECT_ROOT / "data" / "parsed"
SEMANTIC_ROOT = PROJECT_ROOT / "data" / "semantic"
VALIDATION_ROOT = PROJECT_ROOT / "data" / "validation"

SUPPORTED_STORES = {"costco", "emart", "hanaro"}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def ensure_output_dirs(store: str) -> None:
    ensure_dir(PARSED_ROOT / store)
    ensure_dir(SEMANTIC_ROOT / store)
    ensure_dir(VALIDATION_ROOT / store)


def infer_store_from_path(file_path: Path) -> Optional[str]:
    parts = [p.lower() for p in file_path.parts]
    for store in SUPPORTED_STORES:
        if store in parts:
            return store

    name = file_path.name.lower()
    for store in SUPPORTED_STORES:
        if store in name:
            return store

    return None


def load_json(file_path: Path) -> Dict[str, Any]:
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(file_path: Path, data: Dict[str, Any]) -> None:
    ensure_dir(file_path.parent)
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def collect_input_files(input_path: Path) -> List[Path]:
    if input_path.is_file():
        return [input_path]

    if input_path.is_dir():
        return sorted([p for p in input_path.rglob("*.json") if p.is_file()])

    raise FileNotFoundError(f"입력 경로를 찾을 수 없습니다: {input_path}")


def build_output_path(base_root: Path, store: str, file_name: str) -> Path:
    return base_root / store / file_name


# =========================================================
# 🔥 파일명 결정 로직 (핵심 수정)
# =========================================================
def resolve_output_file_name(receipt: Dict[str, Any], file_path: Path) -> str:
    """
    우선순위:
    1. receipt["file_name"]
    2. receipt["source"]
    3. receipt["file_meta"]["parent_name"]
    4. 실제 파일명
    """

    if receipt.get("file_name"):
        return receipt["file_name"]

    if receipt.get("source"):
        return receipt["source"]

    file_meta = receipt.get("file_meta") or {}
    if file_meta.get("parent_name"):
        return f"{file_meta['parent_name']}.json"

    return file_path.name


def process_one_file(file_path: Path, store: Optional[str] = None) -> Dict[str, Any]:
    receipt = load_json(file_path)

    resolved_store = store or receipt.get("store") or infer_store_from_path(file_path)
    if not resolved_store:
        raise ValueError(
            f"store를 결정할 수 없습니다: {file_path}. "
            f"파일 내부 store를 넣거나, costco/emart/hanaro 폴더 아래에 두세요."
        )

    resolved_store = resolved_store.lower()
    if resolved_store not in SUPPORTED_STORES:
        raise ValueError(f"지원하지 않는 store입니다: {resolved_store}")

    # 파일명 결정
    output_file_name = resolve_output_file_name(receipt, file_path)

    # file_name 없으면 채워줌 (semantic/validation에서 사용됨)
    if "file_name" not in receipt or not receipt.get("file_name"):
        receipt["file_name"] = output_file_name

    # store 값도 확정해서 downstream에 전달
    receipt["store"] = resolved_store

    parsed = parse_receipt(receipt, store=resolved_store)
    semantic = interpret_receipt(parsed, store=resolved_store)
    validation = validate_receipt(semantic)

    ensure_output_dirs(resolved_store)

    parsed_path = build_output_path(PARSED_ROOT, resolved_store, output_file_name)
    semantic_path = build_output_path(SEMANTIC_ROOT, resolved_store, output_file_name)
    validation_path = build_output_path(VALIDATION_ROOT, resolved_store, output_file_name)

    save_json(parsed_path, parsed)
    save_json(semantic_path, semantic)
    save_json(validation_path, validation)

    return {
        "input_file": str(file_path),
        "store": resolved_store,
        "parsed_path": str(parsed_path),
        "semantic_path": str(semantic_path),
        "validation_path": str(validation_path),
        "is_valid": validation.get("is_valid"),
        "error_count": len(validation.get("errors", [])),
        "warning_count": len(validation.get("warnings", [])),
    }


def run_pipeline(input_path: str, store: Optional[str] = None) -> List[Dict[str, Any]]:
    path = Path(input_path)
    files = collect_input_files(path)

    normalized_store = store.lower() if store else None
    if normalized_store and normalized_store not in SUPPORTED_STORES:
        raise ValueError(f"지원하지 않는 store입니다: {normalized_store}")

    results: List[Dict[str, Any]] = []

    for file_path in files:
        try:
            result = process_one_file(file_path, store=normalized_store)
            results.append(result)

            print(f"[OK] {file_path.name}")
            print(f"     store           : {result['store']}")
            print(f"     parsed         -> {result['parsed_path']}")
            print(f"     semantic       -> {result['semantic_path']}")
            print(f"     validation     -> {result['validation_path']}")
            print(f"     is_valid       : {result['is_valid']}")
            print(f"     errors/warnings: {result['error_count']}/{result['warning_count']}")
        except Exception as e:
            results.append({
                "input_file": str(file_path),
                "store": normalized_store,
                "is_valid": False,
                "error": str(e),
            })

            print(f"[FAIL] {file_path.name}")
            print(f"       reason: {e}")

    return results


if __name__ == "__main__":
    run_pipeline(str(RAW_ROOT / "costco"), store="costco")
    run_pipeline(str(RAW_ROOT / "emart"), store="emart")
    run_pipeline(str(RAW_ROOT / "hanaro"), store="hanaro")