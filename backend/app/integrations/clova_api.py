import json
import os
import time
import uuid
from pathlib import Path
from typing import Dict, List, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()

CLOVA_API_URL = os.getenv("CLOVA_OCR_API_URL")
CLOVA_SECRET_KEY = os.getenv("CLOVA_OCR_SECRET_KEY")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}


def _validate_env() -> None:
    if not CLOVA_API_URL or not CLOVA_SECRET_KEY:
        raise RuntimeError("CLOVA OCR 환경변수가 설정되지 않았습니다.")


def _validate_file_name(file_name: str) -> str:
    if not file_name or "." not in file_name:
        raise ValueError("올바른 파일명이 필요합니다.")

    extension = file_name.rsplit(".", 1)[-1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(f"지원하지 않는 파일 형식입니다: {extension}")

    return extension


def request_ocr(file_bytes: bytes, file_name: str) -> dict:
    _validate_env()

    if not file_bytes:
        raise ValueError("업로드된 파일 데이터가 비어 있습니다.")

    extension = _validate_file_name(file_name)
    base_name = os.path.splitext(file_name)[0]

    request_body = {
        "images": [{"format": extension, "name": base_name}],
        "requestId": str(uuid.uuid4()),
        "version": "V2",
        "timestamp": int(round(time.time() * 1000)),
    }

    payload = {
        "message": json.dumps(request_body).encode("UTF-8")
    }

    headers = {
        "X-OCR-SECRET": CLOVA_SECRET_KEY
    }

    files = [
        ("file", (file_name, file_bytes))
    ]

    try:
        response = requests.post(
            CLOVA_API_URL,
            headers=headers,
            data=payload,
            files=files,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout as e:
        raise RuntimeError("Clova OCR 요청 시간 초과") from e
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else "unknown"
        body = e.response.text if e.response is not None else ""
        raise RuntimeError(f"Clova OCR HTTP 오류 ({status_code}): {body}") from e
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Clova OCR 요청 오류: {e}") from e


def request_ocr_from_path(file_path: str) -> dict:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"OCR 대상 파일이 존재하지 않습니다: {file_path}")

    file_name = path.name
    _validate_file_name(file_name)

    with path.open("rb") as f:
        file_bytes = f.read()

    return request_ocr(file_bytes=file_bytes, file_name=file_name)


def request_ocr_batch(file_inputs: List[Tuple[bytes, str]]) -> List[Dict]:
    if not file_inputs:
        raise ValueError("업로드된 파일이 없습니다.")

    results: List[Dict] = []

    for file_bytes, file_name in file_inputs:
        result = request_ocr(file_bytes=file_bytes, file_name=file_name)
        results.append(result)

    return results