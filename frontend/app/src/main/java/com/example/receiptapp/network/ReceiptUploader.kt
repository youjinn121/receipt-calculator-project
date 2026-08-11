package com.example.receiptapp.network

import android.content.Context
import android.net.Uri
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File
import java.io.FileOutputStream
import com.example.receiptapp.network.CategoryUpdateItemRequest
import com.example.receiptapp.network.CategoryBulkUpdateRequest
import com.example.receiptapp.network.CategoryBulkUpdateData

object ReceiptUploader {

    suspend fun uploadReceiptImage(
        context: Context,
        imageUri: Uri
    ): Int {
        val file = uriToFile(context, imageUri)

        val requestBody = file
            .asRequestBody("image/jpeg".toMediaTypeOrNull())

        val multipartBody = MultipartBody.Part.createFormData(
            name = "files",
            filename = file.name,
            body = requestBody
        )

        val response = RetrofitClient.apiService.uploadReceipt(multipartBody)
        return response.data.resolvedReceiptId
    }

    suspend fun updateStore(
        receiptId: Int,
        store: String
    ): StoreUpdateData {
        val response = RetrofitClient.apiService.updateReceiptStore(
            receiptId = receiptId,
            request = StoreUpdateRequest(store = store)
        )

        return response.data
    }

    suspend fun runOcr(receiptId: Int) {
        RetrofitClient.apiService.runOcr(receiptId)
    }

    suspend fun runParser(receiptId: Int): ReceiptParserResponse {
        return RetrofitClient.apiService.runParser(receiptId)
    }

    suspend fun getReceiptDetail(receiptId: Int): ReceiptDetailData {
        return RetrofitClient.apiService.getReceiptDetail(receiptId).data
    }

    suspend fun getCompletedReceipts(): List<ReceiptSummaryData> {
        return RetrofitClient.apiService.getCompletedReceipts().data
    }

    suspend fun deleteReceipt(receiptId: Int): DeleteReceiptData {
        return RetrofitClient.apiService.deleteReceipt(receiptId).data
    }

    suspend fun updateReceiptItemCategories(
        receiptId: Int,
        items: List<CategoryUpdateItemRequest>
    ): CategoryBulkUpdateData {
        val response = RetrofitClient.apiService.updateReceiptItemCategories(
            receiptId = receiptId,
            request = CategoryBulkUpdateRequest(items = items)
        )

        return response.data
    }

    private fun uriToFile(context: Context, uri: Uri): File {
        val inputStream = context.contentResolver.openInputStream(uri)
            ?: throw IllegalArgumentException("이미지 파일을 열 수 없습니다.")

        val file = File(
            context.cacheDir,
            "UPLOAD_RECEIPT_${System.currentTimeMillis()}.jpg"
        )

        FileOutputStream(file).use { output ->
            inputStream.copyTo(output)
        }

        return file
    }
}