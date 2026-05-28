package com.example.receiptapp.network

import okhttp3.MultipartBody
import retrofit2.http.Body
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.GET
import retrofit2.http.DELETE

interface ApiService {

    @Multipart
    @POST("receipts/upload")
    suspend fun uploadReceipt(
        @Part files: MultipartBody.Part
    ): ReceiptUploadResponse

    @PATCH("receipts/{receiptId}/store")
    suspend fun updateReceiptStore(
        @Path("receiptId") receiptId: Int,
        @Body request: StoreUpdateRequest
    ): StoreUpdateResponse

    @POST("receipts/{receiptId}/run-ocr")
    suspend fun runOcr(
        @Path("receiptId") receiptId: Int
    ): ReceiptOcrResponse

    @POST("receipts/{receiptId}/run-parser")
    suspend fun runParser(
        @Path("receiptId") receiptId: Int
    ): ReceiptParserResponse

    @GET("receipts/{receiptId}")
    suspend fun getReceiptDetail(
        @Path("receiptId") receiptId: Int
    ): ReceiptDetailResponse

    @DELETE("receipts/{receiptId}")
    suspend fun deleteReceipt(
        @Path("receiptId") receiptId: Int
    ): DeleteReceiptResponse

    @PATCH("receipts/{receiptId}/items/categories")
    suspend fun updateReceiptItemCategories(
        @Path("receiptId") receiptId: Int,
        @Body request: CategoryBulkUpdateRequest
    ): CategoryBulkUpdateResponse

    @GET("receipts")
    suspend fun getCompletedReceipts(): ReceiptListResponse
}
