package com.example.receiptapp.screen

import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.ReceiptLong
import androidx.compose.material.icons.filled.Verified
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.rememberAsyncImagePainter
import com.example.receiptapp.network.ReceiptDetailData
import com.example.receiptapp.network.ReceiptDetailItemData
import com.example.receiptapp.network.ReceiptUploader
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.TextButton
import androidx.compose.foundation.Canvas
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.material.icons.filled.CameraAlt

@Composable
fun ReceiptResultScreen(
    receiptId: Int,
    analyzedAtText: String,
    originalReceiptImageUri: Uri?,
    onBackClick: (() -> Unit)? = null,
    onAnalyzeClick: () -> Unit,
    onDeleteClick: () -> Unit,
    onRetakeClick: () -> Unit
) {
    var receiptDetail by remember { mutableStateOf<ReceiptDetailData?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(receiptId) {
        try {
            isLoading = true
            errorMessage = null
            receiptDetail = ReceiptUploader.getReceiptDetail(receiptId)
        } catch (e: Exception) {
            errorMessage = e.message ?: "영수증 상세 조회에 실패했습니다."
        } finally {
            isLoading = false
        }
    }

    when {
        isLoading -> {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color(0xFFF8FAFD)),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator(color = Color(0xFF1769FF))
            }
        }

        errorMessage != null -> {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color(0xFFF8FAFD))
                    .padding(24.dp),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = errorMessage ?: "오류가 발생했습니다.",
                    color = Color(0xFFEF4444),
                    fontSize = 14.sp
                )
            }
        }

        receiptDetail != null -> {
            ReceiptResultContent(
                data = receiptDetail!!,
                analyzedAtText = analyzedAtText,
                originalReceiptImageUri = originalReceiptImageUri,
                onBackClick = onBackClick,
                onAnalyzeClick = onAnalyzeClick,
                onDeleteClick = onDeleteClick,
                onRetakeClick = onRetakeClick
            )
        }
    }
}

@Composable
private fun ReceiptResultContent(
    data: ReceiptDetailData,
    analyzedAtText: String,
    originalReceiptImageUri: Uri?,
    onBackClick: (() -> Unit)?,
    onAnalyzeClick: () -> Unit,
    onDeleteClick: () -> Unit,
    onRetakeClick: () -> Unit
) {
    var showOriginalReceipt by remember { mutableStateOf(false) }
    var showDeleteDialog by remember { mutableStateOf(false) }

    val shouldShowRecaptureScreen =
        !data.is_valid || data.recapture_recommended

    if (shouldShowRecaptureScreen) {
        RecaptureRequiredFullScreen(
            onBackClick = onBackClick,
            onRetakeClick = onRetakeClick
        )
        return
    }

    val items = data.items
    val productCount = items.size
    val paymentTotal = data.payment_total ?: 0
    val itemTotal = data.item_total ?: items.sumOf { it.final_price ?: 0 }
    val receiptDiscountTotal = data.receipt_discount_total ?: 0
    val calculatedTotal =
        itemTotal - receiptDiscountTotal + (data.fee_total ?: 0)

    val storeText = when (data.store?.lowercase()) {
        "costco" -> "COSTCO"
        "emart" -> "이마트"
        "hanaro" -> "하나로마트"
        else -> data.store?.uppercase() ?: "영수증"
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF8FAFD))
    ) {
        Column(
            modifier = Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 18.dp)
        ) {
            TopBar(
                onBackClick = onBackClick,
                onDeleteClick = {
                    showDeleteDialog = true
                }
            )

            StoreHeader(
                storeText = storeText,
                analyzedAtText = analyzedAtText,
                imageUri = originalReceiptImageUri,
                isValid = data.is_valid
            )

            Spacer(modifier = Modifier.height(18.dp))

            CompactSummaryBox(
                paymentTotal = paymentTotal,
                productCount = data.items.sumOf { item -> item.qty ?: 1 }
            )

            Spacer(modifier = Modifier.height(18.dp))

            PurchaseSectionHeader(
                onOriginalReceiptClick = {
                    showOriginalReceipt = true
                }
            )

            Spacer(modifier = Modifier.height(8.dp))

            PurchaseTable(items = items)

            Spacer(modifier = Modifier.height(14.dp))

            PaymentSummaryCard(
                itemTotal = itemTotal,
                receiptDiscountTotal = receiptDiscountTotal,
                paymentTotal = paymentTotal
            )

            Spacer(modifier = Modifier.height(14.dp))

            ValidationResultCard(
                totalMatch = data.validation?.total_match,
                isTotalInferred = data.is_total_inferred,
                calculatedTotal = calculatedTotal,
                paymentTotal = paymentTotal
            )

            Spacer(modifier = Modifier.height(16.dp))
        }

        Button(
            onClick = onAnalyzeClick,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 18.dp)
                .height(58.dp),
            shape = RoundedCornerShape(12.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = Color(0xFF1769FF)
            )
        ) {
            Box(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = "분석 결과 보기",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White,
                    modifier = Modifier.align(Alignment.Center)
                )

                Icon(
                    imageVector = Icons.Default.KeyboardArrowRight,
                    contentDescription = "분석 결과 보기",
                    tint = Color.White,
                    modifier = Modifier
                        .align(Alignment.CenterEnd)
                        .size(30.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(22.dp))
    }

    if (showOriginalReceipt) {
        OriginalReceiptDialog(
            imageUri = originalReceiptImageUri,
            onDismiss = { showOriginalReceipt = false }
        )
    }

    if (showDeleteDialog) {
        AlertDialog(
            onDismissRequest = {
                showDeleteDialog = false
            },
            title = {
                Text(
                    text = "영수증 삭제",
                    fontWeight = FontWeight.Bold
                )
            },
            text = {
                Text("이 영수증을 삭제하시겠습니까?")
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        showDeleteDialog = false
                        onDeleteClick()
                    }
                ) {
                    Text(
                        text = "삭제",
                        color = Color(0xFFEF4444),
                        fontWeight = FontWeight.Bold
                    )
                }
            },
            dismissButton = {
                TextButton(
                    onClick = {
                        showDeleteDialog = false
                    }
                ) {
                    Text("취소")
                }
            }
        )
    }
}

@Composable
private fun TopBar(
    onBackClick: (() -> Unit)?,
    onDeleteClick: () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(58.dp),
        contentAlignment = Alignment.Center
    ) {
        if (onBackClick != null) {
            IconButton(
                onClick = onBackClick,
                modifier = Modifier.align(Alignment.CenterStart)
            ) {
                Icon(
                    imageVector = Icons.Default.ArrowBack,
                    contentDescription = "뒤로가기",
                    tint = Color(0xFF172033)
                )
            }
        }

        Text(
            text = "영수증 상세",
            fontSize = 19.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF172033)
        )

        IconButton(
            onClick = onDeleteClick,
            modifier = Modifier.align(Alignment.CenterEnd)
        ) {
            Icon(
                imageVector = Icons.Default.Delete,
                contentDescription = "영수증 삭제",
                tint = Color(0xFF172033)
            )
        }
    }
}

@Composable
private fun StoreHeader(
    storeText: String,
    analyzedAtText: String,
    imageUri: Uri?,
    isValid: Boolean
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(70.dp)
                .clip(RoundedCornerShape(10.dp))
                .background(Color.White)
                .border(1.dp, Color(0xFFE1E7F0), RoundedCornerShape(10.dp)),
            contentAlignment = Alignment.Center
        ) {
            if (imageUri != null) {
                Image(
                    painter = rememberAsyncImagePainter(imageUri),
                    contentDescription = "영수증 이미지",
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Crop
                )
            } else {
                Icon(
                    imageVector = Icons.Default.ReceiptLong,
                    contentDescription = "영수증",
                    tint = Color(0xFF1769FF),
                    modifier = Modifier.size(32.dp)
                )
            }
        }

        Spacer(modifier = Modifier.width(14.dp))

        Column(
            modifier = Modifier.weight(1f)
        ) {
            Text(
                text = storeText,
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF172033)
            )

            Spacer(modifier = Modifier.height(7.dp))

            Text(
                text = analyzedAtText.ifBlank { "-" },
                fontSize = 13.sp,
                color = Color(0xFF8A94A6)
            )
        }

        Box(
            modifier = Modifier
                .clip(RoundedCornerShape(20.dp))
                .background(if (isValid) Color(0xFFDDF7E8) else Color(0xFFFFE8E8))
                .padding(horizontal = 12.dp, vertical = 7.dp),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = if (isValid) "완료" else "검증 필요",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = if (isValid) Color(0xFF1B9E5A) else Color(0xFFEF4444)
            )
        }
    }
}

@Composable
private fun CompactSummaryBox(
    paymentTotal: Int,
    productCount: Int
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .height(60.dp),
        shape = RoundedCornerShape(16.dp),
        color = Color.White,
        shadowElevation = 2.dp
    ) {
        Row(
            modifier = Modifier.fillMaxSize(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            SummaryHalf(
                modifier = Modifier.weight(1f),
                title = "결제 금액",
                value = "${formatPrice(paymentTotal)}원"
            )

            Box(
                modifier = Modifier
                    .width(1.dp)
                    .height(44.dp)
                    .background(Color(0xFFE2E7EF))
            )

            SummaryHalf(
                modifier = Modifier.weight(1f),
                title = "상품 수",
                value = "${productCount}개"
            )
        }
    }
}

@Composable
private fun SummaryHalf(
    modifier: Modifier = Modifier,
    title: String,
    value: String
) {
    Column(
        modifier = modifier.fillMaxHeight(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = title,
            fontSize = 13.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color(0xFF7B8494)
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = value,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF172033)
        )
    }
}

@Composable
private fun PurchaseSectionHeader(
    onOriginalReceiptClick: () -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = "구매 목록",
            fontSize = 17.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF172033),
            modifier = Modifier.weight(1f)
        )

        OutlinedButton(
            onClick = onOriginalReceiptClick,
            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 5.dp),
            shape = RoundedCornerShape(20.dp),
            colors = ButtonDefaults.outlinedButtonColors(
                contentColor = Color(0xFF172033)
            )
        ) {
            Text(
                text = "원본 영수증 보기",
                fontSize = 12.sp,
                color = Color(0xFF172033)
            )

            Spacer(modifier = Modifier.width(4.dp))

            Icon(
                imageVector = Icons.Default.KeyboardArrowRight,
                contentDescription = "원본 영수증 보기",
                modifier = Modifier.size(18.dp)
            )
        }
    }
}

@Composable
private fun PurchaseTable(
    items: List<ReceiptDetailItemData>
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        color = Color.White,
        shadowElevation = 2.dp
    ) {
        Column {
            PurchaseTableHeader()

            items.forEachIndexed { index, item ->
                PurchaseTableRow(item)

                if (index != items.lastIndex) {
                    HorizontalDivider(
                        modifier = Modifier.padding(horizontal = 12.dp),
                        color = Color(0xFFE8EDF5),
                        thickness = 1.dp
                    )
                }
            }
        }
    }
}

@Composable
private fun PurchaseTableHeader() {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0xFFF7F9FC))
            .padding(horizontal = 12.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        TableHeaderText("상품명", Modifier.weight(2.1f), TextAlign.Start)
        TableHeaderText("수량", Modifier.weight(0.7f), TextAlign.Center)
        TableHeaderText("상품 금액", Modifier.weight(1.15f), TextAlign.End)
        TableHeaderText("할인 금액", Modifier.weight(1.15f), TextAlign.End)
        TableHeaderText("합계 금액", Modifier.weight(1.15f), TextAlign.End)
    }
}

@Composable
private fun TableHeaderText(
    text: String,
    modifier: Modifier,
    textAlign: TextAlign
) {
    Text(
        text = text,
        modifier = modifier,
        fontSize = 11.sp,
        fontWeight = FontWeight.SemiBold,
        color = Color(0xFF6B7280),
        textAlign = textAlign
    )
}

@Composable
private fun PurchaseTableRow(
    item: ReceiptDetailItemData
) {
    val qty = item.qty ?: 0
    val basePrice = item.base_price ?: item.final_price ?: 0
    val discount = item.discount ?: 0
    val finalPrice = item.final_price ?: 0

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 15.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = item.name ?: "상품명 없음",
            modifier = Modifier.weight(2.1f),
            fontSize = 12.5.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF172033),
            maxLines = 2
        )

        Text(
            text = qty.toString(),
            modifier = Modifier.weight(0.7f),
            fontSize = 12.sp,
            color = Color(0xFF172033),
            textAlign = TextAlign.Center
        )

        Text(
            text = formatPrice(basePrice),
            modifier = Modifier.weight(1.15f),
            fontSize = 12.sp,
            color = Color(0xFF172033),
            textAlign = TextAlign.End
        )

        Text(
            text = if (discount > 0) "-${formatPrice(discount)}" else "-",
            modifier = Modifier.weight(1.15f),
            fontSize = 12.sp,
            color = if (discount > 0) Color(0xFFEF4444) else Color(0xFF8A94A6),
            textAlign = TextAlign.End
        )

        Text(
            text = formatPrice(finalPrice),
            modifier = Modifier.weight(1.15f),
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF172033),
            textAlign = TextAlign.End
        )
    }
}

@Composable
private fun PaymentSummaryCard(
    itemTotal: Int,
    receiptDiscountTotal: Int,
    paymentTotal: Int
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        color = Color.White,
        shadowElevation = 2.dp
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 18.dp, vertical = 17.dp)
        ) {
            SummaryLine(
                label = "상품 금액 합계",
                value = formatPrice(itemTotal)
            )

            Spacer(modifier = Modifier.height(14.dp))

            SummaryLine(
                label = "추가 할인",
                value = if (receiptDiscountTotal > 0) "-${formatPrice(receiptDiscountTotal)}" else "0",
                isDiscount = receiptDiscountTotal > 0
            )

            Spacer(modifier = Modifier.height(16.dp))

            HorizontalDivider(color = Color(0xFFE8EDF5))

            Spacer(modifier = Modifier.height(16.dp))

            SummaryLine(
                label = "최종 결제 금액",
                value = "${formatPrice(paymentTotal)}원",
                isTotal = true
            )
        }
    }
}

@Composable
private fun SummaryLine(
    label: String,
    value: String,
    isDiscount: Boolean = false,
    isTotal: Boolean = false
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = label,
            fontSize = if (isTotal) 15.sp else 13.sp,
            fontWeight = if (isTotal) FontWeight.Bold else FontWeight.SemiBold,
            color = Color(0xFF172033)
        )

        Text(
            text = value,
            fontSize = if (isTotal) 24.sp else 13.sp,
            fontWeight = FontWeight.Bold,
            color = when {
                isTotal -> Color(0xFF1769FF)
                isDiscount -> Color(0xFFEF4444)
                else -> Color(0xFF172033)
            }
        )
    }
}

@Composable
private fun ValidationResultCard(
    totalMatch: Boolean?,
    isTotalInferred: Boolean,
    calculatedTotal: Int,
    paymentTotal: Int
) {
    val diff = kotlin.math.abs(calculatedTotal - paymentTotal)

    val accentColor = when {
        isTotalInferred -> Color(0xFFA78BFA)
        totalMatch == true -> Color(0xFF1769FF)
        else -> Color(0xFFFF9800)
    }

    val cardColor = when {
        isTotalInferred -> Color(0xFFFAF5FF)
        totalMatch == true -> Color(0xFFF4F7FF)
        else -> Color(0xFFFFFAF2)
    }

    val iconText = when {
        isTotalInferred -> "?"
        totalMatch == true -> "✓"
        else -> "!"
    }

    val badgeText = when {
        isTotalInferred -> "자동 추정"
        totalMatch == true -> "일치"
        else -> "확인 필요"
    }

    val resultText = when {
        isTotalInferred ->
            "상품 금액 합계를 바탕으로 결제 금액을 자동으로 추정했습니다.\n영수증 정보를 확인해주세요."

        totalMatch == true ->
            "계산된 금액과 인식한 결제 금액이 일치합니다."

        totalMatch == false ->
            "${formatPrice(diff)}원 차이가 있습니다.\n영수증 정보를 확인해주세요."

        else ->
            "영수증 정보를 확인해주세요."
    }

    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        color = cardColor,
        shadowElevation = 1.dp
    ) {
        Column(
            modifier = Modifier.padding(18.dp)
        ) {

            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {

                Box(
                    modifier = Modifier
                        .size(34.dp)
                        .clip(CircleShape)
                        .background(accentColor),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = iconText,
                        color = Color.White,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold
                    )
                }

                Spacer(modifier = Modifier.width(10.dp))

                Text(
                    text = "검증 결과",
                    fontSize = 21.sp,
                    fontWeight = FontWeight.Bold,
                    color = accentColor
                )

                Spacer(modifier = Modifier.weight(1f))

                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(20.dp))
                        .background(accentColor.copy(alpha = 0.12f))
                        .padding(horizontal = 12.dp, vertical = 6.dp)
                ) {
                    Text(
                        text = badgeText,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = accentColor
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(accentColor.copy(alpha = 0.08f))
                    .padding(horizontal = 14.dp, vertical = 13.dp)
            ) {
                Text(
                    text = resultText,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium,
                    color = accentColor,
                    lineHeight = 19.sp
                )
            }
        }
    }
}


@Composable
private fun OriginalReceiptDialog(
    imageUri: Uri?,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("닫기")
            }
        },
        title = {
            Text(
                text = "원본 영수증",
                fontWeight = FontWeight.Bold
            )
        },
        text = {
            if (imageUri != null) {
                Image(
                    painter = rememberAsyncImagePainter(imageUri),
                    contentDescription = "원본 영수증",
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(480.dp)
                        .clip(RoundedCornerShape(12.dp)),
                    contentScale = ContentScale.Fit
                )
            } else {
                Text("표시할 영수증 이미지가 없습니다.")
            }
        }
    )
}

fun formatPrice(value: Int): String {
    return "%,d".format(value)
}

@Composable
private fun RecaptureRequiredCard(
    onRetakeClick: () -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        color = Color(0xFFFFF1F1),
        shadowElevation = 2.dp
    ) {
        Column(
            modifier = Modifier.padding(18.dp)
        ) {
            Text(
                text = "영수증 정보를 정확히 확인하지 못했어요",
                fontSize = 16.sp,
                fontWeight = FontWeight.ExtraBold,
                color = Color(0xFFDC2626)
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "일부 상품 또는 금액 정보가 누락되었을 수 있습니다.\n더 선명하게 다시 촬영해 주세요.",
                fontSize = 13.sp,
                lineHeight = 19.sp,
                fontWeight = FontWeight.Medium,
                color = Color(0xFF7F1D1D)
            )

            Spacer(modifier = Modifier.height(14.dp))

            Button(
                onClick = onRetakeClick,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFFDC2626),
                    contentColor = Color.White
                )
            ) {
                Text(
                    text = "다시 촬영하기",
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}

@Composable
private fun RecaptureRequiredFullScreen(
    onBackClick: (() -> Unit)?,
    onRetakeClick: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(64.dp),
            contentAlignment = Alignment.Center
        ) {
            if (onBackClick != null) {
                IconButton(
                    onClick = onBackClick,
                    modifier = Modifier.align(Alignment.CenterStart)
                ) {
                    Icon(
                        imageVector = Icons.Default.ArrowBack,
                        contentDescription = "뒤로가기",
                        tint = Color(0xFF111827),
                        modifier = Modifier.size(30.dp)
                    )
                }
            }

            Text(
                text = "영수증 결과",
                fontSize = 22.sp,
                fontWeight = FontWeight.ExtraBold,
                color = Color(0xFF172033)
            )
        }

        Divider(color = Color(0xFFE5E7EB), thickness = 1.dp)

        Column(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = 28.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            ReceiptWarningIllustration()

            Spacer(modifier = Modifier.height(35.dp))

            Text(
                text = "영수증 정보를 정확히 인식하지 못했어요.\n다시 촬영해 주세요.",
                fontSize = 20.sp,
                lineHeight = 38.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF172033),
                textAlign = TextAlign.Center
            )
        }

        Button(
            onClick = onRetakeClick,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 16.dp)
                .height(64.dp),
            shape = RoundedCornerShape(12.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = Color(0xFF0758F9),
                contentColor = Color.White
            )
        ) {
            Icon(
                imageVector = Icons.Default.CameraAlt,
                contentDescription = "다시 촬영하기",
                modifier = Modifier.size(26.dp)
            )

            Spacer(modifier = Modifier.width(12.dp))

            Text(
                text = "다시 촬영하기",
                fontSize = 19.sp,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

@Composable
private fun ReceiptWarningIllustration() {
    Box(
        modifier = Modifier.size(270.dp),
        contentAlignment = Alignment.Center
    ) {
        Box(
            modifier = Modifier
                .size(230.dp)
                .background(Color(0xFFEAF3FF), CircleShape)
        )

        Surface(
            modifier = Modifier
                .width(126.dp)
                .height(178.dp),
            color = Color.White,
            shape = RoundedCornerShape(4.dp),
            shadowElevation = 8.dp
        ) {
            Column(
                modifier = Modifier.padding(horizontal = 18.dp, vertical = 22.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = "RECEIPT",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.ExtraBold,
                    color = Color(0xFF8B8F98)
                )

                Spacer(modifier = Modifier.height(24.dp))

                repeat(5) { index ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Box(
                            modifier = Modifier
                                .width(if (index % 2 == 0) 58.dp else 42.dp)
                                .height(7.dp)
                                .clip(RoundedCornerShape(4.dp))
                                .background(Color(0xFFE1E3E8))
                        )

                        Box(
                            modifier = Modifier
                                .width(18.dp)
                                .height(7.dp)
                                .clip(RoundedCornerShape(4.dp))
                                .background(Color(0xFFE1E3E8))
                        )
                    }

                    Spacer(modifier = Modifier.height(12.dp))
                }

                Spacer(modifier = Modifier.weight(1f))

                Canvas(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(34.dp)
                ) {
                    val stroke = 3.dp.toPx()
                    val gap = size.width / 16f

                    for (i in 0..14) {
                        val x = i * gap
                        drawLine(
                            color = Color(0xFF6B7280),
                            start = Offset(x, 0f),
                            end = Offset(x, size.height),
                            strokeWidth = if (i % 3 == 0) stroke else stroke / 1.6f,
                            cap = StrokeCap.Square
                        )
                    }
                }
            }
        }

        Box(
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .offset(x = (-20).dp, y = (-18).dp)
                .size(86.dp)
                .background(Color(0xFF1769FF), CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "!",
                fontSize = 56.sp,
                fontWeight = FontWeight.ExtraBold,
                color = Color.White
            )
        }

        Canvas(
            modifier = Modifier
                .align(Alignment.CenterEnd)
                .size(68.dp)
                .offset(x = 8.dp, y = (-10).dp)
        ) {
            val blue = Color(0xFF1769FF)
            val stroke = 4.dp.toPx()

            drawLine(blue, Offset(10f, 8f), Offset(14f, 30f), stroke, cap = StrokeCap.Round)
            drawLine(blue, Offset(42f, 18f), Offset(24f, 36f), stroke, cap = StrokeCap.Round)
            drawLine(blue, Offset(48f, 54f), Offset(66f, 54f), stroke, cap = StrokeCap.Round)
        }
    }
}