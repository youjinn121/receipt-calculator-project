package com.example.receiptapp

import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ReceiptLong
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Home
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.example.receiptapp.navigation.BottomNavItem
import com.example.receiptapp.navigation.CustomBottomNavigation
import com.example.receiptapp.network.ReceiptLocalStore
import com.example.receiptapp.network.ReceiptUploader
import com.example.receiptapp.screen.*
import com.example.receiptapp.ui.theme.ReceiptAppTheme
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            ReceiptAppTheme {
                MainScreen()
            }
        }
    }
}

@Composable
fun MainScreen() {
    var selectedIndex by remember { mutableIntStateOf(0) }
    var uploadScreenMode by remember { mutableStateOf("upload") }

    var capturedImageUri by remember { mutableStateOf<Uri?>(null) }
    var croppedReceiptImageUri by remember { mutableStateOf<Uri?>(null) }

    var selectedStore by remember { mutableStateOf("") }

    var uploadedReceiptId by remember { mutableStateOf<Int?>(null) }
    var selectedReceiptId by remember { mutableStateOf<Int?>(null) }

    var uploadErrorMessage by remember { mutableStateOf<String?>(null) }

    var originalReceiptImageUri by remember { mutableStateOf<Uri?>(null) }
    var selectedReceiptImageUri by remember { mutableStateOf<Uri?>(null) }

    var analyzedAtText by remember { mutableStateOf("") }

    var savedReceipts by remember { mutableStateOf<List<ReceiptListUi>>(emptyList()) }

    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    val galleryLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri ->
        if (uri != null) {
            capturedImageUri = uri
            originalReceiptImageUri = uri
            selectedReceiptImageUri = uri
            croppedReceiptImageUri = null

            uploadedReceiptId = null
            selectedReceiptId = null
            uploadErrorMessage = null
            selectedStore = ""
            analyzedAtText = ""

            uploadScreenMode = "crop"
        }
    }

    LaunchedEffect(Unit) {

        try {

            val completedReceipts =
                ReceiptUploader.getCompletedReceipts()

            savedReceipts = completedReceipts.map { receipt ->

                val storeName = when (receipt.store?.lowercase()) {
                    "costco" -> "코스트코"
                    "emart" -> "이마트"
                    "hanaro" -> "하나로마트"
                    else -> receipt.store ?: "영수증"
                }

                ReceiptListUi(
                    id = receipt.receipt_id,
                    storeName = storeName,
                    analyzedAtText = receipt.analyzed_at
                        ?.replace("T", " ")
                        ?.take(16)
                        ?: "날짜 정보 없음",
                    paymentTotal = receipt.payment_total ?: 0,
                    imageUri = null
                )
            }

        } catch (e: Exception) {
            uploadErrorMessage =
                e.message ?: "영수증 목록을 불러오지 못했습니다."
        }
    }

    val navItems = listOf(
        BottomNavItem("홈", Icons.Default.Home),
        BottomNavItem("영수증", Icons.AutoMirrored.Filled.ReceiptLong),
        BottomNavItem("장바구니 분석", Icons.Default.Dashboard)
    )

    val hideBottomNav =
        selectedIndex == 0 && uploadScreenMode in listOf(
            "camera",
            "crop",
            "store",
            "processing",
            "result"
        )

    Scaffold(
        containerColor = Color(0xFFF8FAFD),
        bottomBar = {
            if (!hideBottomNav) {
                CustomBottomNavigation(
                    items = navItems,
                    selectedIndex = selectedIndex,
                    onItemClick = {
                        selectedIndex = it
                    }
                )
            }
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(if (hideBottomNav) PaddingValues(0.dp) else innerPadding)
                .padding(
                    start = if (hideBottomNav) 0.dp else 24.dp,
                    end = if (hideBottomNav) 0.dp else 24.dp,
                    top = if (hideBottomNav) 0.dp else 24.dp
                ),
            contentAlignment = Alignment.Center
        ) {
            when (selectedIndex) {
                0 -> {
                    when (uploadScreenMode) {
                        "upload" -> {
                            UploadScreen(
                                onCameraClick = {
                                    capturedImageUri = null
                                    croppedReceiptImageUri = null
                                    originalReceiptImageUri = null
                                    selectedReceiptImageUri = null
                                    uploadedReceiptId = null
                                    selectedReceiptId = null
                                    uploadErrorMessage = null
                                    selectedStore = ""
                                    analyzedAtText = ""

                                    uploadScreenMode = "camera"
                                },
                                onGalleryClick = {
                                    galleryLauncher.launch("image/*")
                                }
                            )
                        }

                        "camera" -> {
                            CameraScreen(
                                onCloseClick = {
                                    uploadScreenMode = "upload"
                                },
                                onPhotoCaptured = { uri ->
                                    capturedImageUri = uri
                                    originalReceiptImageUri = uri
                                    selectedReceiptImageUri = uri
                                    uploadScreenMode = "crop"
                                }
                            )
                        }

                        "crop" -> {
                            CropScreen(
                                imageUri = capturedImageUri,
                                onRetakeClick = {
                                    capturedImageUri = null
                                    croppedReceiptImageUri = null
                                    originalReceiptImageUri = null
                                    selectedReceiptImageUri = null
                                    uploadScreenMode = "camera"
                                },
                                onCompleteClick = { croppedUri ->
                                    if (croppedUri == null) {
                                        uploadErrorMessage = "크롭된 이미지가 없습니다."
                                        return@CropScreen
                                    }

                                    croppedReceiptImageUri = croppedUri
                                    originalReceiptImageUri = croppedUri
                                    selectedReceiptImageUri = croppedUri

                                    uploadedReceiptId = null
                                    selectedReceiptId = null
                                    uploadErrorMessage = null
                                    uploadScreenMode = "store"
                                }
                            )
                        }

                        "store" -> {
                            StoreSelectScreen(
                                selectedStore = selectedStore,
                                onStoreSelected = { store ->
                                    selectedStore = store
                                },
                                onBackClick = {
                                    uploadScreenMode = "crop"
                                },
                                onStartClick = {
                                    if (selectedStore.isBlank()) {
                                        uploadErrorMessage = "store를 선택하세요."
                                        return@StoreSelectScreen
                                    }

                                    analyzedAtText = SimpleDateFormat(
                                        "yyyy-MM-dd HH:mm",
                                        Locale.KOREA
                                    ).format(Date())

                                    coroutineScope.launch {
                                        try {
                                            uploadScreenMode = "processing"

                                            val imageUri = croppedReceiptImageUri

                                            if (imageUri == null) {
                                                uploadErrorMessage = "업로드할 이미지가 없습니다."
                                                uploadScreenMode = "store"
                                                return@launch
                                            }

                                            val receiptId = ReceiptUploader.uploadReceiptImage(
                                                context = context,
                                                imageUri = imageUri
                                            )

                                            uploadedReceiptId = receiptId
                                            selectedReceiptId = receiptId

                                            ReceiptUploader.updateStore(
                                                receiptId = receiptId,
                                                store = selectedStore
                                            )

                                            ReceiptUploader.runOcr(receiptId)
                                            ReceiptUploader.runParser(receiptId)

                                            val detail = ReceiptUploader.getReceiptDetail(receiptId)

                                            val storeName = when (detail.store?.lowercase()) {
                                                "costco" -> "코스트코"
                                                "emart" -> "이마트"
                                                "hanaro" -> "하나로마트"
                                                else -> detail.store ?: "영수증"
                                            }

                                            val shouldRecapture =
                                                !detail.is_valid || detail.recapture_recommended

                                            val finalImageUri = if (shouldRecapture) {
                                                croppedReceiptImageUri
                                            } else {
                                                val permanentImageUri = croppedReceiptImageUri?.let { uri ->
                                                    ReceiptLocalStore.saveImagePermanently(
                                                        context = context,
                                                        receiptId = detail.receipt_id,
                                                        imageUri = uri
                                                    )
                                                }

                                                permanentImageUri ?: croppedReceiptImageUri
                                            }

                                            if (!shouldRecapture) {

                                                val displayAnalyzedAtText = detail.analyzed_at
                                                    ?.replace("T", " ")
                                                    ?.take(16)
                                                    ?: analyzedAtText

                                                val newReceipt = ReceiptListUi(
                                                    id = detail.receipt_id,
                                                    storeName = storeName,
                                                    analyzedAtText = displayAnalyzedAtText,
                                                    paymentTotal = detail.payment_total ?: 0,
                                                    imageUri = finalImageUri
                                                )

                                                ReceiptLocalStore.saveReceipt(
                                                    context = context,
                                                    receiptId = detail.receipt_id,
                                                    analyzedAtText = displayAnalyzedAtText,
                                                    imageUri = finalImageUri
                                                )

                                                savedReceipts =
                                                    listOf(newReceipt) + savedReceipts.filter {
                                                        it.id != detail.receipt_id
                                                    }

                                            } else {

                                                ReceiptLocalStore.removeReceiptId(
                                                    context = context,
                                                    receiptId = detail.receipt_id
                                                )

                                                savedReceipts = savedReceipts.filter {
                                                    it.id != detail.receipt_id
                                                }
                                            }

                                            selectedReceiptId = receiptId
                                            uploadedReceiptId = receiptId
                                            selectedReceiptImageUri = finalImageUri
                                            originalReceiptImageUri = finalImageUri
                                            croppedReceiptImageUri = finalImageUri

                                            uploadErrorMessage = null
                                            uploadScreenMode = "result"
                                        } catch (e: Exception) {
                                            e.printStackTrace()
                                            uploadErrorMessage = e.message
                                            uploadScreenMode = "store"
                                        }
                                    }
                                }
                            )
                        }

                        "processing" -> {
                            ProcessingScreen()
                        }

                        "result" -> {
                            val receiptId = uploadedReceiptId

                            if (receiptId != null && receiptId > 0) {
                                ReceiptResultScreen(
                                    receiptId = receiptId,
                                    analyzedAtText = analyzedAtText,
                                    originalReceiptImageUri = selectedReceiptImageUri
                                        ?: originalReceiptImageUri
                                        ?: croppedReceiptImageUri,
                                    onBackClick = {
                                        selectedIndex = 1
                                        uploadScreenMode = "upload"
                                    },
                                    onAnalyzeClick = {
                                        selectedReceiptId = receiptId
                                        selectedIndex = 2
                                        uploadScreenMode = "upload"
                                    },
                                    onDeleteClick = {
                                        coroutineScope.launch {
                                            try {
                                                ReceiptUploader.deleteReceipt(receiptId)
                                                ReceiptLocalStore.removeReceiptId(
                                                    context,
                                                    receiptId
                                                )

                                                savedReceipts = savedReceipts.filter {
                                                    it.id != receiptId
                                                }

                                                uploadedReceiptId = null
                                                selectedReceiptId = null
                                                selectedReceiptImageUri = null
                                                originalReceiptImageUri = null
                                                croppedReceiptImageUri = null
                                                capturedImageUri = null

                                                selectedIndex = 1
                                                uploadScreenMode = "upload"
                                            } catch (e: Exception) {
                                                e.printStackTrace()
                                                uploadErrorMessage = e.message
                                            }
                                        }
                                    },
                                    onRetakeClick = {
                                        capturedImageUri = null
                                        croppedReceiptImageUri = null
                                        originalReceiptImageUri = null
                                        selectedReceiptImageUri = null
                                        uploadedReceiptId = null
                                        selectedReceiptId = null
                                        uploadErrorMessage = null
                                        selectedStore = ""
                                        analyzedAtText = ""

                                        selectedIndex = 0
                                        uploadScreenMode = "camera"
                                    }
                                )
                            } else {
                                Text("영수증 ID를 찾을 수 없습니다.")
                            }
                        }
                    }
                }

                1 -> {
                    ReceiptScreen(
                        receipts = savedReceipts,
                        onReceiptClick = { receipt ->
                            selectedReceiptId = receipt.id
                            uploadedReceiptId = receipt.id

                            selectedReceiptImageUri = receipt.imageUri
                            originalReceiptImageUri = receipt.imageUri
                            croppedReceiptImageUri = receipt.imageUri
                            analyzedAtText = receipt.analyzedAtText

                            selectedIndex = 0
                            uploadScreenMode = "result"
                        }
                    )
                }

                2 -> {
                    DashboardScreen(
                        receipts = savedReceipts,
                        selectedReceiptId = selectedReceiptId,
                        onReceiptSelected = { receipt ->
                            selectedReceiptId = receipt.id
                            uploadedReceiptId = receipt.id

                            selectedReceiptImageUri = receipt.imageUri
                            originalReceiptImageUri = receipt.imageUri
                            croppedReceiptImageUri = receipt.imageUri
                            analyzedAtText = receipt.analyzedAtText
                        }
                    )
                }
            }
        }
    }
}