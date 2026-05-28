package com.example.receiptapp.network

data class ReceiptUploadResponse(
    val message: String,
    val data: ReceiptUploadData
)

data class ReceiptUploadData(
    val receipt_id: Int? = null,
    val id: Int? = null
) {
    val resolvedReceiptId: Int
        get() = receipt_id ?: id ?: -1
}

data class StoreUpdateRequest(
    val store: String
)

data class StoreUpdateResponse(
    val message: String,
    val data: StoreUpdateData
)

data class StoreUpdateData(
    val receipt_id: Int,
    val store: String,
    val status: String
)

data class ReceiptOcrResponse(
    val message: String,
    val data: ReceiptOcrData
)

data class ReceiptOcrData(
    val receipt_id: Int,
    val status: String,
    val image_count: Int
)

data class ReceiptParserResponse(
    val message: String,
    val data: ReceiptParserData
)

data class ReceiptParserData(
    val receipt_id: Int? = null,
    val status: String? = null,
    val analyzed_at: String? = null,
    val semantic: SemanticData? = null
)

data class SemanticData(
    val store: String? = null,
    val items: List<ReceiptItemData> = emptyList()
)

data class ReceiptItemData(
    val name: String? = null,
    val qty: Int? = null,
    val unit_price: Int? = null,
    val final_price: Int? = null
)

data class ReceiptDetailResponse(
    val message: String,
    val data: ReceiptDetailData
)

data class ReceiptDetailData(
    val receipt_id: Int,
    val file_name: String? = null,
    val store: String? = null,
    val status: String? = null,
    val analyzed_at: String? = null,

    val item_total: Int? = null,
    val payment_total: Int? = null,
    val receipt_discount_total: Int? = null,
    val fee_total: Int? = null,

    val is_valid: Boolean = false,
    val recapture_recommended: Boolean = false,
    val is_total_inferred: Boolean = false,
    val requires_user_total_confirmation: Boolean = false,

    val items: List<ReceiptDetailItemData> = emptyList(),
    val validation: ReceiptDetailValidationData? = null,
    val analysis: ReceiptDetailAnalysisData? = null
)

data class ReceiptDetailItemData(
    val id: Int? = null,
    val name: String? = null,
    val normalized_name: String? = null,
    val category: String? = null,
    val category_source: String? = null,
    val code: String? = null,
    val qty: Int? = null,
    val unit_price: Int? = null,
    val base_price: Int? = null,
    val discount: Int? = null,
    val final_price: Int? = null
)

data class ReceiptDetailValidationData(
    val checked_item_count: Int? = null,
    val valid_item_count: Int? = null,
    val invalid_item_count: Int? = null,
    val total_match: Boolean? = null,
    val subtotal_segment_match: Boolean? = null,
    val categorization_rate: Double? = null,
    val error_count: Int? = null,
    val warning_count: Int? = null
)

data class ReceiptDetailAnalysisData(
    val guilty_pleasure_index: Double? = null,
    val home_cooking_independence: Double? = null,
    val guilty_pleasure_amount: Int? = null,
    val home_food_amount: Int? = null,
    val total_final_price: Int? = null
)

data class DeleteReceiptResponse(
    val message: String,
    val data: DeleteReceiptData
)

data class DeleteReceiptData(
    val receipt_id: Int,
    val deleted: Boolean
)

data class CategoryUpdateItemRequest(
    val item_id: Int,
    val category: String
)

data class CategoryBulkUpdateRequest(
    val items: List<CategoryUpdateItemRequest>
)

data class CategoryBulkUpdateResponse(
    val message: String,
    val data: CategoryBulkUpdateData
)

data class CategoryBulkUpdateData(
    val receipt_id: Int,
    val updated_count: Int
)

data class ReceiptSummaryData(
    val receipt_id: Int,
    val file_name: String? = null,
    val store: String? = null,
    val status: String? = null,
    val analyzed_at: String? = null,
    val payment_total: Int? = null,
    val is_valid: Boolean = false,
    val recapture_recommended: Boolean = false
)

data class ReceiptListResponse(
    val message: String,
    val data: List<ReceiptSummaryData>
)