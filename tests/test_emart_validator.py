from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from semantic.emart_interpreter import interpret_receipt
from validation.validator import validate_receipt


BASE_DIR = Path(__file__).resolve().parent.parent

PARSED_DIR = BASE_DIR / "data" / "parsed" / "emart"
RAW_DIR = BASE_DIR / "data" / "raw" / "emart"

SEMANTIC_DIR = BASE_DIR / "data" / "semantic" / "emart"
VALIDATION_DIR = BASE_DIR / "data" / "validation" / "emart"


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_parsed_receipt(data: Dict[str, Any]) -> bool:
    if not isinstance(data, dict):
        return False

    lines = data.get("lines")
    if not isinstance(lines, list) or not lines:
        return False

    first = lines[0]
    if not isinstance(first, dict):
        return False

    return "line_type" in first


def find_input_file() -> Path:
    parsed_files = sorted(PARSED_DIR.glob("*.json"))
    if parsed_files:
        return parsed_files[0]

    raw_files = sorted(RAW_DIR.glob("result_*.json"))
    if raw_files:
        return raw_files[0]

    raise FileNotFoundError(
        f"입력 json 파일을 찾지 못했습니다.\n"
        f"- parsed dir: {PARSED_DIR}\n"
        f"- raw dir: {RAW_DIR}"
    )


def run_emart_validation_test(input_json_path: Path) -> Dict[str, Any]:
    receipt_data = load_json(input_json_path)

    if not is_parsed_receipt(receipt_data):
        raise ValueError(
            f"이 파일은 parsed 결과가 아닙니다: {input_json_path}\n"
            f"emart_interpreter 입력은 line_type이 포함된 parsed json 이어야 합니다."
        )

    semantic_receipt = interpret_receipt(receipt_data)
    validation_result = validate_receipt(semantic_receipt)

    return {
        "parsed_receipt": receipt_data,
        "semantic_receipt": semantic_receipt,
        "validation_result": validation_result,
    }


if __name__ == "__main__":
    input_json_path = find_input_file()
    print(f"[TEST FILE] {input_json_path}")

    result = run_emart_validation_test(input_json_path)

    print("\n[semantic 결과]")
    print(json.dumps(result["semantic_receipt"], ensure_ascii=False, indent=2))

    print("\n[validation 결과]")
    print(json.dumps(result["validation_result"], ensure_ascii=False, indent=2))

    output_name = input_json_path.name
    save_json(SEMANTIC_DIR / output_name, result["semantic_receipt"])
    save_json(VALIDATION_DIR / output_name, result["validation_result"])