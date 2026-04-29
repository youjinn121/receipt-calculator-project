"""
[Validator Router]

스토어별 validator로 라우팅
"""

from typing import Any, Dict

from validation.costco_validator import validate_costco
from validation.emart_validator import validate_emart
from validation.hanaro_validator import validate_hanaro


def validate_receipt(semantic_receipt: Dict[str, Any]) -> Dict[str, Any]:
    store = (semantic_receipt.get("store") or "").lower()

    if store == "costco":
        return validate_costco(semantic_receipt)

    if store == "emart":
        return validate_emart(semantic_receipt)

    if store == "hanaro":
        return validate_hanaro(semantic_receipt)

    raise ValueError(f"Unsupported store: {store}")