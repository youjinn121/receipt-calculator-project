from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Callable

from semantic.emart_interpreter import interpret_receipt
from validation.validator import validate_receipt


BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "raw" / "emart"
PARSED_DIR = BASE_DIR / "data" / "parsed" / "emart"
SEMANTIC_DIR = BASE_DIR / "data" / "semantic" / "emart"
VALIDATION_DIR = BASE_DIR / "data" / "validation" / "emart"


def _resolve_parser() -> Callable[[str], Dict[str, Any]]:
    """
    parser_pipeline 함수명이 아직 고정되지 않았을 수 있어서
    대표적인 이름들을 순서대로 시도한다.
    """
    try:
        from receipt_parser.parser_pipeline import parse_receipt  # type: ignore
        return parse_receipt
    except Exception:
        pass

    try:
        from receipt_parser.parser_pipeline import run_parse_pipeline_for_single_receipt  # type: ignore
        return run_parse_pipeline_for_single_receipt
    except Exception:
        pass

    try:
        from receipt_parser.parser_pipeline import run_parser_for_single_receipt  # type: ignore
        return run_parser_for_single_receipt
    except Exception:
        pass

    raise ImportError(
        "receipt_parser.parser_pipeline 안에서 단일 영수증 parser 함수를 찾지 못했습니다.\n"
        "parse_receipt(...) 같은 단일 파일용 함수를 확인해서 import 한 줄만 맞춰주세요."
    )


PARSE_RECEIPT = _resolve_parser()


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Callable

from semantic.emart_interpreter import interpret_receipt
from validation.validator import validate_receipt


BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "raw" / "emart"
PARSED_DIR = BASE_DIR / "data" / "parsed" / "emart"
SEMANTIC_DIR = BASE_DIR / "data" / "semantic" / "emart"
VALIDATION_DIR = BASE_DIR / "data" / "validation" / "emart"


def _resolve_parser() -> Callable[[str], Any]:
    try:
        from receipt_parser.parser_pipeline import parse_receipt  # type: ignore
        return parse_receipt
    except Exception:
        pass

    try:
        from receipt_parser.parser_pipeline import run_parse_pipeline_for_single_receipt  # type: ignore
        return run_parse_pipeline_for_single_receipt
    except Exception:
        pass

    try:
        from receipt_parser.parser_pipeline import run_parser_for_single_receipt  # type: ignore
        return run_parser_for_single_receipt
    except Exception:
        pass

    raise ImportError(
        "receipt_parser.parser_pipeline 안에서 단일 영수증 parser 함수를 찾지 못했습니다."
    )


PARSE_RECEIPT = _resolve_parser()


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _normalize_parsed_output(parsed_output: Any) -> Dict[str, Any]:
    if isinstance(parsed_output, dict):
        return parsed_output

    if isinstance(parsed_output, str):
        parsed_output = parsed_output.strip()

        # JSON 문자열
        if parsed_output.startswith("{") or parsed_output.startswith("["):
            data = json.loads(parsed_output)
            if isinstance(data, dict):
                return data
            raise TypeError("parser returned JSON string, but top-level is not dict.")

        # 파일 경로 문자열
        possible_path = Path(parsed_output)
        if possible_path.exists():
            return load_json(possible_path)

    raise TypeError(
        f"parser output type이 예상과 다릅니다: {type(parsed_output).__name__}"
    )


def run_one(raw_json_path: Path) -> Dict[str, Any]:
    print(f"\n[RUN] {raw_json_path.name}")

    raw_parsed_output = PARSE_RECEIPT(str(raw_json_path))
    parsed_receipt = _normalize_parsed_output(raw_parsed_output)

    file_name = parsed_receipt.get("file_name")
    if not file_name:
        stem = raw_json_path.stem
        if stem.startswith("result_"):
            file_name = f"{stem[len('result_'):]}.json"
        else:
            file_name = f"{stem}.json"
        parsed_receipt["file_name"] = file_name

    if not parsed_receipt.get("store"):
        parsed_receipt["store"] = "emart"

    semantic_receipt = interpret_receipt(parsed_receipt)
    validation_result = validate_receipt(semantic_receipt)

    parsed_out_path = PARSED_DIR / file_name
    semantic_out_path = SEMANTIC_DIR / file_name
    validation_out_path = VALIDATION_DIR / file_name

    save_json(parsed_out_path, parsed_receipt)
    save_json(semantic_out_path, semantic_receipt)
    save_json(validation_out_path, validation_result)

    print(f"  parsed     -> {parsed_out_path}")
    print(f"  semantic   -> {semantic_out_path}")
    print(f"  validation -> {validation_out_path}")
    print(
        f"  is_valid={validation_result.get('is_valid')} | "
        f"total_match={validation_result.get('receipt_validation', {}).get('total_match')}"
    )

    return {
        "parsed_receipt": parsed_receipt,
        "semantic_receipt": semantic_receipt,
        "validation_result": validation_result,
    }


def main() -> None:
    raw_files = sorted(RAW_DIR.glob("result_*.json"))

    if not raw_files:
        raise FileNotFoundError(f"raw emart json 파일이 없습니다: {RAW_DIR}")

    print(f"[RAW FILE COUNT] {len(raw_files)}")

    success_count = 0
    failed_count = 0

    for raw_json_path in raw_files:
        try:
            run_one(raw_json_path)
            success_count += 1
        except Exception as e:
            failed_count += 1
            print(f"\n[FAILED] {raw_json_path.name}")
            print(f"  {type(e).__name__}: {e}")

    print("\n[SUMMARY]")
    print(f"  success={success_count}")
    print(f"  failed={failed_count}")


if __name__ == "__main__":
    main()