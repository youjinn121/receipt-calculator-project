from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ReceiptImageUploadResult(BaseModel):
    page_no: int
    file_path: str


class ReceiptUploadResponseData(BaseModel):
    receipt_id: int
    status: str
    image_count: int
    images: List[ReceiptImageUploadResult]


class ReceiptUploadResponse(BaseModel):
    message: str
    data: ReceiptUploadResponseData


class ReceiptImageOcrResult(BaseModel):
    page_no: int
    file_path: str
    ocr_json_path: Optional[str] = None


class ReceiptOcrResponseData(BaseModel):
    receipt_id: int
    status: str
    image_count: int
    images: List[ReceiptImageOcrResult]


class ReceiptOcrResponse(BaseModel):
    message: str
    data: ReceiptOcrResponseData
    
    
class ReceiptStoreUpdateRequest(BaseModel):
    store: str


class ReceiptStoreUpdateResponseData(BaseModel):
    receipt_id: int
    store: str
    status: str


class ReceiptStoreUpdateResponse(BaseModel):
    message: str
    data: ReceiptStoreUpdateResponseData
    

class ReceiptParserResponseData(BaseModel):
    receipt_id: int
    status: str
    file_name: str
    line_count: int
    file_meta: Dict[str, Any] = {}
    lines: List[Dict[str, Any]] = []
    semantic: Dict[str, Any] = {}
    validation: Dict[str, Any] = {}


class ReceiptParserResponse(BaseModel):
    message: str
    data: ReceiptParserResponseData