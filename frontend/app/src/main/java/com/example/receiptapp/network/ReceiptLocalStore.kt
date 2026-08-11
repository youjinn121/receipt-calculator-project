package com.example.receiptapp.network

import android.content.Context
import android.net.Uri
import java.io.File
import java.io.FileOutputStream

data class SavedReceiptMeta(
    val receiptId: Int,
    val analyzedAtText: String,
    val imageUriString: String?
)

object ReceiptLocalStore {
    private const val PREF_NAME = "receipt_local_store"

    private const val KEY_RECEIPT_IDS = "receipt_ids"
    private const val KEY_DATE_PREFIX = "receipt_date_"
    private const val KEY_IMAGE_PREFIX = "receipt_image_"

    fun saveReceipt(
        context: Context,
        receiptId: Int,
        analyzedAtText: String,
        imageUri: Uri?
    ) {
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)

        val currentIds = getReceiptIds(context).toMutableList()

        if (!currentIds.contains(receiptId)) {
            currentIds.add(0, receiptId)
        } else {
            currentIds.remove(receiptId)
            currentIds.add(0, receiptId)
        }

        prefs.edit()
            .putString(KEY_RECEIPT_IDS, currentIds.joinToString(","))
            .putString(KEY_DATE_PREFIX + receiptId, analyzedAtText)
            .putString(KEY_IMAGE_PREFIX + receiptId, imageUri?.toString())
            .apply()
    }

    fun saveReceiptId(context: Context, receiptId: Int) {
        saveReceipt(
            context = context,
            receiptId = receiptId,
            analyzedAtText = "",
            imageUri = null
        )
    }

    fun getReceiptIds(context: Context): List<Int> {
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        val raw = prefs.getString(KEY_RECEIPT_IDS, "") ?: ""

        return raw
            .split(",")
            .mapNotNull { it.toIntOrNull() }
            .distinct()
    }

    fun getSavedReceipts(context: Context): List<SavedReceiptMeta> {
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)

        return getReceiptIds(context).map { receiptId ->
            SavedReceiptMeta(
                receiptId = receiptId,
                analyzedAtText = prefs.getString(KEY_DATE_PREFIX + receiptId, "") ?: "",
                imageUriString = prefs.getString(KEY_IMAGE_PREFIX + receiptId, null)
            )
        }
    }

    fun removeReceiptId(context: Context, receiptId: Int) {
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)

        val updatedIds = getReceiptIds(context)
            .filter { it != receiptId }

        prefs.edit()
            .putString(KEY_RECEIPT_IDS, updatedIds.joinToString(","))
            .remove(KEY_DATE_PREFIX + receiptId)
            .remove(KEY_IMAGE_PREFIX + receiptId)
            .apply()
    }

    fun saveImagePermanently(
        context: Context,
        receiptId: Int,
        imageUri: Uri
    ): Uri? {
        return try {
            val inputStream = context.contentResolver.openInputStream(imageUri)
                ?: return null

            val outputDir = File(context.filesDir, "saved_receipt_images")
            if (!outputDir.exists()) {
                outputDir.mkdirs()
            }

            val outputFile = File(outputDir, "receipt_$receiptId.jpg")

            FileOutputStream(outputFile).use { output ->
                inputStream.copyTo(output)
            }

            inputStream.close()

            Uri.fromFile(outputFile)
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }
}