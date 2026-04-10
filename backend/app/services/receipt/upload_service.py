import os
import uuid
from typing import List

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from backend.app.models.receipt.receipt_image import ReceiptImage
from backend.app.services.receipt.receipt_service import create_receipt

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/jpg"}
UPLOAD_ROOT = "backend/storage/receipts"

async def save_uploaded_receipt_files(db: Session, files: List[UploadFile]):
    if not files:
        raise HTTPException(status_code=400, detail="업로드된 파일이 없습니다.")

    for file in files:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 파일 형식입니다: {file.filename}"
            )

    first_file_name = files[0].filename or "receipt"
    receipt = create_receipt(db=db, file_name=first_file_name)

    receipt_dir = os.path.join(UPLOAD_ROOT, str(receipt.id))
    os.makedirs(receipt_dir, exist_ok=True)

    saved_images = []

    for idx, file in enumerate(files, start=1):
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in [".jpg", ".jpeg", ".png"]:
            ext = ".png"

        stored_filename = f"page_{idx}_{uuid.uuid4().hex}{ext}"
        stored_path = os.path.join(receipt_dir, stored_filename)

        content = await file.read()
        with open(stored_path, "wb") as f:
            f.write(content)

        image = ReceiptImage(
            receipt_id=receipt.id,
            page_no=idx,
            file_path=stored_path,
        )
        db.add(image)

        saved_images.append({
            "page_no": idx,
            "file_path": stored_path,
        })

    db.commit()

    return {
        "receipt_id": receipt.id,
        "status": receipt.status,
        "image_count": len(saved_images),
        "images": saved_images,
    }