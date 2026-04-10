import json
import os
from typing import Any, Dict

from backend.app.integrations.clova_api import request_ocr_from_path


def build_ocr_json_path(image_path: str) -> str:
    base, _ = os.path.splitext(image_path)
    return f"{base}.ocr.json"


def save_ocr_result_to_file(image_path: str, ocr_result: Dict[str, Any]) -> str:
    json_path = build_ocr_json_path(image_path)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(ocr_result, f, ensure_ascii=False, indent=2)

    return json_path


def run_ocr_for_image(image_path: str) -> str:
    ocr_result = request_ocr_from_path(image_path)
    json_path = save_ocr_result_to_file(image_path=image_path, ocr_result=ocr_result)
    return json_path