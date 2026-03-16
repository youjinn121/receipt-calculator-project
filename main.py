from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile

from clova_api import request_ocr_batch
from parser import run_parser

try:
    from interpreter import interpret_receipt
except ImportError:
    interpret_receipt = None

try:
    from calculator import calculate_receipt
except ImportError:
    calculate_receipt = None


app = FastAPI(title="Receipt API")


@app.get("/")
def get_health():
    return {"status": "ok"}


@app.post("/upload-receipt")
async def upload_receipt(
    files: List[UploadFile] = File(...),
    payment_id: Optional[str] = None,
):
    try:
        if not files:
            raise HTTPException(status_code=400, detail="업로드된 파일이 없습니다.")

        file_inputs = []
        file_names = []

        for file in files:
            file_bytes = await file.read()

            if not file_bytes:
                raise HTTPException(
                    status_code=400,
                    detail=f"비어 있는 파일이 포함되어 있습니다: {file.filename}",
                )

            file_inputs.append((file_bytes, file.filename))
            file_names.append(file.filename)

        raw_ocr_results = request_ocr_batch(file_inputs)
        parsed_lines = parse_receipt_pages(raw_ocr_results, file_names)

        if interpret_receipt is not None:
            interpreted_items = interpret_receipt(parsed_lines)
        else:
            interpreted_items = []

        if calculate_receipt is not None:
            calculation_result = calculate_receipt(interpreted_items)
        else:
            calculation_result = {
                "items": interpreted_items,
                "total": None,
                "status": "calculator_not_implemented",
            }

        return {
            "payment_id": payment_id,
            "file_count": len(files),
            "file_names": file_names,
            "raw_ocr_results": raw_ocr_results,
            "parsed_lines": parsed_lines,
            "interpreted_items": interpreted_items,
            "calculation": calculation_result,
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {e}")
