import os
import json
import time
import uuid
import requests
from dotenv import load_dotenv

load_dotenv()

CLOVA_API_URL = os.getenv("CLOVA_OCR_API_URL")
CLOVA_SECRET_KEY = os.getenv("CLOVA_OCR_SECRET_KEY")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}


def request_ocr(file_bytes: bytes, file_name: str) -> dict:
    if not CLOVA_API_URL or not CLOVA_SECRET_KEY:
        raise RuntimeError("CLOVA OCR 환경변수가 설정되지 않았습니다.")

    if not file_bytes:
        raise ValueError("업로드된 파일 데이터가 비어 있습니다.")

    if not file_name or "." not in file_name:
        raise ValueError("올바른 파일명이 필요합니다.")

    extension = file_name.rsplit(".", 1)[-1].lower()
    base_name = os.path.splitext(file_name)[0]

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("지원하지 않는 파일 형식입니다.")

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
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Clova OCR 요청 오류: {e}") from e


def request_ocr_batch(file_inputs: list[tuple[bytes, str]]) -> list[dict]:
    if not file_inputs:
        raise ValueError("업로드된 파일이 없습니다.")

    results = []

    for file_bytes, file_name in file_inputs:
        result = request_ocr(file_bytes, file_name)
        results.append(result)

    return results
