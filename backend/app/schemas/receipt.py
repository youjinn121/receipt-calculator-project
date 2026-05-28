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
    
class ReceiptDetailItem(BaseModel):
    id: int
    name: str
    normalized_name: Optional[str] = None
    category: Optional[str] = None
    category_source: Optional[str] = None
    code: Optional[str] = None
    qty: Optional[int] = None
    unit_price: Optional[int] = None
    base_price: Optional[int] = None
    discount: Optional[int] = None
    final_price: Optional[int] = None


class ReceiptDetailValidation(BaseModel):
    checked_item_count: Optional[int] = None
    valid_item_count: Optional[int] = None
    invalid_item_count: Optional[int] = None
    total_match: Optional[bool] = None
    subtotal_segment_match: Optional[bool] = None
    categorization_rate: Optional[float] = None
    error_count: Optional[int] = None
    warning_count: Optional[int] = None

class ReceiptDetailAnalysis(BaseModel):
    guilty_pleasure_index: Optional[float] = None
    home_cooking_independence: Optional[float] = None
    guilty_pleasure_amount: Optional[int] = None
    home_food_amount: Optional[int] = None
    total_final_price: Optional[int] = None
    
class ReceiptDetailData(BaseModel):
    receipt_id: int
    file_name: str
    store: Optional[str] = None
    status: str

    item_total: Optional[int] = None
    payment_total: Optional[int] = None
    receipt_discount_total: Optional[int] = None
    fee_total: Optional[int] = None

    is_valid: bool
    recapture_recommended: bool
    is_total_inferred: bool
    requires_user_total_confirmation: bool

    items: List[ReceiptDetailItem] = []
    validation: Optional[ReceiptDetailValidation] = None
    analysis: Optional[ReceiptDetailAnalysis] = None
    analyzed_at: Optional[str] = None


class ReceiptDetailResponse(BaseModel):
    message: str
    data: ReceiptDetailData
    
class ReceiptItemCategoryUpdateItem(BaseModel):
    item_id: int
    category: str

class ReceiptItemCategoryBulkUpdateRequest(BaseModel):
    items: List[ReceiptItemCategoryUpdateItem]

class ReceiptItemCategoryBulkUpdateData(BaseModel):
    receipt_id: int
    updated_count: int

class ReceiptItemCategoryBulkUpdateResponse(BaseModel):
    message: str
    data: ReceiptItemCategoryBulkUpdateData