from __future__ import annotations

from typing import Any, Dict

from receipt_parser.parser_pipeline import parse_receipt
from semantic.semantic_manager import interpret_receipt
from validation.validator import validate_receipt


def run_receipt_pipeline(receipt: Dict[str, Any], store: str) -> Dict[str, Any]:

    resolved_store = (store or "").strip().lower()
    if not resolved_store:
        raise ValueError("store 값이 필요합니다.")

    parsed = parse_receipt(receipt=receipt, store=resolved_store)
    semantic = interpret_receipt(parsed, store=resolved_store)
    validation = validate_receipt(semantic)

    return {
        "parsed": parsed,
        "semantic": semantic,
        "validation": validation,
    }