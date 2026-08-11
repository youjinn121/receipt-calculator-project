package com.example.receiptapp.screen

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.receiptapp.network.CategoryUpdateItemRequest
import com.example.receiptapp.network.ReceiptDetailData
import com.example.receiptapp.network.ReceiptDetailItemData
import com.example.receiptapp.network.ReceiptUploader
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale
import kotlinx.coroutines.launch
import kotlin.math.abs
import kotlin.math.ceil
import androidx.compose.ui.graphics.nativeCanvas
import android.graphics.Paint


private val AllowedCategories = listOf(
    "식재료",
    "간편식",
    "간식",
    "음료",
    "주류",
    "생활용품",
    "반려동물",
    "기타"
)

private enum class TendencyPeriod {
    DAILY, WEEKLY, MONTHLY
}

private enum class TrendPeriod {
    WEEKLY, MONTHLY
}

private data class CategorySpendingUi(
    val name: String,
    val amount: Int,
    val percent: Double
)

private data class HomeCookingUi(
    val ingredientAmount: Int,
    val convenienceAmount: Int,
    val totalAmount: Int,
    val ratio: Double
)

private data class GuiltyPleasureUi(
    val guiltyAmount: Int,
    val totalPayment: Int,
    val ratio: Double
)

private data class TrendRatioPointUi(
    val label: String,
    val ratio: Double
)

private data class TrendAmountPointUi(
    val label: String,
    val amount: Int
)

@Composable
fun DashboardScreen(
    receipts: List<ReceiptListUi>,
    selectedReceiptId: Int?,
    onReceiptSelected: (ReceiptListUi) -> Unit
) {
    var categoryPeriod by remember {
        mutableStateOf(TendencyPeriod.DAILY)
    }

    var homeCookingPeriod by remember {
        mutableStateOf(TendencyPeriod.DAILY)
    }

    var guiltyPleasurePeriod by remember {
        mutableStateOf(TendencyPeriod.DAILY)
    }

    var currentDate by remember {
        mutableStateOf(todayCalendarForTendency())
    }

    LaunchedEffect(selectedReceiptId, receipts) {
        val targetReceipt = receipts.firstOrNull { it.id == selectedReceiptId }

        if (targetReceipt != null) {
            categoryPeriod = TendencyPeriod.DAILY
            homeCookingPeriod = TendencyPeriod.DAILY
            guiltyPleasurePeriod = TendencyPeriod.DAILY
            currentDate =
                parseCalendarForTendency(targetReceipt.analyzedAtText)
                    ?: todayCalendarForTendency()
        }
    }

    var details by remember { mutableStateOf<List<ReceiptDetailData>>(emptyList()) }
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    var isCategoryEditMode by remember { mutableStateOf(false) }
    var editTargetDetail by remember { mutableStateOf<ReceiptDetailData?>(null) }
    var isSavingCategories by remember { mutableStateOf(false) }
    var trendCategory by remember { mutableStateOf<String?>(null) }

    val coroutineScope = rememberCoroutineScope()

    LaunchedEffect(receipts) {
        try {
            isLoading = true
            errorMessage = null
            details = receipts.map { ReceiptUploader.getReceiptDetail(it.id) }
        } catch (e: Exception) {
            errorMessage = e.message ?: "분석 정보를 불러오지 못했습니다."
        } finally {
            isLoading = false
        }
    }

    if (isCategoryEditMode && editTargetDetail != null) {
        CategoryEditScreen(
            detail = editTargetDetail!!,
            isSaving = isSavingCategories,
            onBackClick = { isCategoryEditMode = false },
            onSaveClick = { selectedMap ->
                coroutineScope.launch {
                    try {
                        isSavingCategories = true

                        val requestItems = selectedMap.map { (itemId, category) ->
                            CategoryUpdateItemRequest(
                                item_id = itemId,
                                category = category
                            )
                        }

                        ReceiptUploader.updateReceiptItemCategories(
                            receiptId = editTargetDetail!!.receipt_id,
                            items = requestItems
                        )

                        details = receipts.map { ReceiptUploader.getReceiptDetail(it.id) }
                        isCategoryEditMode = false
                    } catch (e: Exception) {
                        errorMessage = e.message ?: "카테고리 저장에 실패했습니다."
                    } finally {
                        isSavingCategories = false
                    }
                }
            }
        )
        return
    }

    if (trendCategory != null) {
        CategoryTrendScreen(
            receipts = receipts,
            details = details,
            initialCategory = trendCategory!!,
            currentDate = currentDate,
            onBackClick = { trendCategory = null }
        )
        return
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .padding(horizontal = 24.dp),
        contentPadding = PaddingValues(bottom = 92.dp)
    ) {
        item {
            Spacer(modifier = Modifier.height(30.dp))

            Text(
                text = "소비 리포트",
                fontSize = 25.sp,
                fontWeight = FontWeight.ExtraBold,
                color = Color(0xFF111827)
            )

            Spacer(modifier = Modifier.height(25.dp))
        }

        item {
            when {
                isLoading -> {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(220.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator(color = Color(0xFF14A99A))
                    }
                }

                errorMessage != null -> {
                    EmptyAnalysisCard(errorMessage ?: "오류가 발생했습니다.")
                }

                else -> {
                    SectionTitle(
                        title = "카테고리별 지출",
                        description = "카테고리별 지출 비중을 한눈에 확인할 수 있어요"
                    )

                    Spacer(modifier = Modifier.height(23.dp))

                    CategorySpendingAnalysisSection(
                        receipts = receipts,
                        details = details,
                        period = categoryPeriod,
                        currentDate = currentDate,
                        onPeriodChange = { categoryPeriod = it },
                        onPrevClick = {
                            currentDate = moveTendencyDate(
                                currentDate,
                                categoryPeriod,
                                -1
                            )
                        },
                        onNextClick = {
                            currentDate = moveTendencyDate(
                                currentDate,
                                categoryPeriod,
                                1
                            )
                        },
                        onEditCategoriesClick = { detail ->
                            editTargetDetail = detail
                            isCategoryEditMode = true
                        },
                        onCategoryTrendClick = { category ->
                            trendCategory = category
                        }
                    )

                    Spacer(modifier = Modifier.height(42.dp))
                    SectionDivider()
                    Spacer(modifier = Modifier.height(32.dp))

                    HomeCookingSection(
                        receipts = receipts,
                        details = details,
                        period = homeCookingPeriod,
                        currentDate = currentDate,
                        onPeriodChange = { homeCookingPeriod = it },
                        onPrevClick = {
                            currentDate = moveTendencyDate(
                                currentDate,
                                homeCookingPeriod,
                                -1
                            )
                        },
                        onNextClick = {
                            currentDate = moveTendencyDate(
                                currentDate,
                                homeCookingPeriod,
                                1
                            )
                        }
                    )

                    Spacer(modifier = Modifier.height(42.dp))
                    SectionDivider()
                    Spacer(modifier = Modifier.height(32.dp))

                    GuiltyPleasureSection(
                        receipts = receipts,
                        details = details,
                        period = guiltyPleasurePeriod,
                        currentDate = currentDate,
                        onPeriodChange = { guiltyPleasurePeriod = it },
                        onPrevClick = {
                            currentDate = moveTendencyDate(
                                currentDate,
                                guiltyPleasurePeriod,
                                -1
                            )
                        },
                        onNextClick = {
                            currentDate = moveTendencyDate(
                                currentDate,
                                guiltyPleasurePeriod,
                                1
                            )
                        }
                    )
                }
            }
        }
    }
}

@Composable
private fun CategorySpendingAnalysisSection(
    receipts: List<ReceiptListUi>,
    details: List<ReceiptDetailData>,
    period: TendencyPeriod,
    currentDate: Calendar,
    onPeriodChange: (TendencyPeriod) -> Unit,
    onPrevClick: () -> Unit,
    onNextClick: () -> Unit,
    onEditCategoriesClick: (ReceiptDetailData) -> Unit,
    onCategoryTrendClick: (String) -> Unit
) {
    val targetDetails = getDetailsInPeriod(
        receipts = receipts,
        details = details,
        period = period,
        currentDate = currentDate
    )

    if (targetDetails.isEmpty()) {
        SpendingPeriodNavigator(
            selectedPeriod = period,
            label = getSpendingPeriodLabel(period, currentDate),
            onPeriodChange = onPeriodChange,
            onPrevClick = onPrevClick,
            onNextClick = onNextClick
        )

        Spacer(modifier = Modifier.height(24.dp))
        EmptyAnalysisCard("선택한 기간에 분석할 영수증이 없습니다.")
        return
    }

    val totalPayment = targetDetails.sumOf { detail ->
        detail.items.sumOf { item -> item.final_price ?: 0 }
    }

    val categories = buildCategorySpendingUi(
        details = targetDetails,
        totalPayment = totalPayment
    )

    val topCategory = categories.firstOrNull()
    val editTarget = targetDetails.firstOrNull()

    Column(modifier = Modifier.fillMaxWidth()) {
        SpendingPeriodNavigator(
            selectedPeriod = period,
            label = getSpendingPeriodLabel(period, currentDate),
            onPeriodChange = onPeriodChange,
            onPrevClick = onPrevClick,
            onNextClick = onNextClick
        )

        Spacer(modifier = Modifier.height(11.dp))

        CategoryDonutChart(
            categories = categories,
            topCategory = topCategory
        )

        Spacer(modifier = Modifier.height(11.dp))

        SpendingTotalRow(totalPayment = totalPayment)

        Spacer(modifier = Modifier.height(8.dp))
        Divider(color = Color(0xFFE5E7EB), thickness = 1.dp)
        Spacer(modifier = Modifier.height(8.dp))

        categories.forEachIndexed { index, category ->
            CategorySpendingRow(
                category = category
            )

            if (index != categories.lastIndex) {
                Spacer(modifier = Modifier.height(8.dp))
            }
        }

        if (editTarget != null) {
            Spacer(modifier = Modifier.height(14.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Button(
                    onClick = { onEditCategoriesClick(editTarget) },
                    modifier = Modifier
                        .weight(1f)
                        .height(42.dp),
                    shape = RoundedCornerShape(14.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Color(0xFFF2F6FF),
                        contentColor = Color(0xFF0B2A6F)
                    ),
                    elevation = ButtonDefaults.buttonElevation(
                        defaultElevation = 0.dp
                    )
                ) {
                    Text(
                        text = "카테고리 구성",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold
                    )
                }

                Button(
                    onClick = {
                        onCategoryTrendClick(topCategory?.name ?: "기타")
                    },
                    modifier = Modifier
                        .weight(1f)
                        .height(42.dp),
                    shape = RoundedCornerShape(14.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Color(0xFFF2F6FF),
                        contentColor = Color(0xFF0B2A6F)
                    ),
                    elevation = ButtonDefaults.buttonElevation(
                        defaultElevation = 0.dp
                    )
                ) {
                    Text(
                        text = "지출 추이",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }
    }
}

@Composable
private fun HomeCookingSection(
    receipts: List<ReceiptListUi>,
    details: List<ReceiptDetailData>,
    period: TendencyPeriod,
    currentDate: Calendar,
    onPeriodChange: (TendencyPeriod) -> Unit,
    onPrevClick: () -> Unit,
    onNextClick: () -> Unit
) {
    var trendPeriod by remember { mutableStateOf(TrendPeriod.WEEKLY) }

    val targetDetails = getDetailsInPeriod(
        receipts = receipts,
        details = details,
        period = period,
        currentDate = currentDate
    )

    val ui = buildHomeCookingUi(targetDetails)

    val trendPoints = buildHomeCookingTrendPoints(
        receipts = receipts,
        details = details,
        trendPeriod = trendPeriod,
        currentDate = currentDate
    )

    val trendCurrentUi = buildHomeCookingUi(
        getDetailsInPeriod(
            receipts = receipts,
            details = details,
            period = trendPeriod.toTendencyPeriod(),
            currentDate = currentDate
        )
    )

    val previousUi = buildPreviousHomeCookingUi(
        receipts = receipts,
        details = details,
        trendPeriod = trendPeriod,
        currentDate = currentDate
    )

    val previousRatio = previousUi?.ratio ?: 0.0

    val diffPoint =
        (trendCurrentUi.ratio - previousRatio) * 100.0

    Column(modifier = Modifier.fillMaxWidth()) {
        SectionTitle(
            title = "홈쿠킹 지수",
            description = "식재료 중심 소비 비율을 확인할 수 있어요"
        )

        Spacer(modifier = Modifier.height(23.dp))

        SpendingPeriodNavigator(
            selectedPeriod = period,
            label = getSpendingPeriodLabel(period, currentDate),
            onPeriodChange = onPeriodChange,
            onPrevClick = onPrevClick,
            onNextClick = onNextClick
        )

        Spacer(modifier = Modifier.height(22.dp))

        HomeCookingGauge(ui = ui)

        Spacer(modifier = Modifier.height(18.dp))

        HomeCookingAmountBox(ui = ui)

        Spacer(modifier = Modifier.height(30.dp))

        TrendPeriodSelector(
            selected = trendPeriod,
            onSelected = { trendPeriod = it }
        )

        CategoryRatioTrendChart(
            points = trendPoints,
            lineColor = Color(0xFF17A99B)
        )

        Spacer(modifier = Modifier.height(-30.dp))

        CompareBox(
            trendPeriod = trendPeriod,
            diffPoint = diffPoint,
            positiveMessage = "식재료 중심 소비 비중이 높아졌어요.",
            negativeMessage = "식재료 중심 소비 비중이 낮아졌어요.",
            sameMessage = "식재료 중심 소비 비중이 유지되고 있어요.",
            accentColor = Color(0xFF16A34A),
            backgroundColor = Color(0xFFEFFDF4)
        )
    }
}

@Composable
private fun GuiltyPleasureSection(
    receipts: List<ReceiptListUi>,
    details: List<ReceiptDetailData>,
    period: TendencyPeriod,
    currentDate: Calendar,
    onPeriodChange: (TendencyPeriod) -> Unit,
    onPrevClick: () -> Unit,
    onNextClick: () -> Unit
) {
    var trendPeriod by remember { mutableStateOf(TrendPeriod.WEEKLY) }

    val targetDetails = getDetailsInPeriod(
        receipts = receipts,
        details = details,
        period = period,
        currentDate = currentDate
    )

    val ui = buildGuiltyPleasureUi(targetDetails)

    val trendPoints = buildGuiltyPleasureTrendPoints(
        receipts = receipts,
        details = details,
        trendPeriod = trendPeriod,
        currentDate = currentDate
    )

    val trendCurrentUi = buildGuiltyPleasureUi(
        getDetailsInPeriod(
            receipts = receipts,
            details = details,
            period = trendPeriod.toTendencyPeriod(),
            currentDate = currentDate
        )
    )

    val previousUi = buildPreviousGuiltyPleasureUi(
        receipts = receipts,
        details = details,
        trendPeriod = trendPeriod,
        currentDate = currentDate
    )

    val previousRatio = previousUi?.ratio ?: 0.0

    val diffPoint =
        (trendCurrentUi.ratio - previousRatio) * 100.0

    Column(modifier = Modifier.fillMaxWidth()) {
        SectionTitle(
            title = "기호성 소비 지수",
            description = "간식·주류 소비 비율을 확인할 수 있어요"
        )

        Spacer(modifier = Modifier.height(12.dp))

        SpendingPeriodNavigator(
            selectedPeriod = period,
            label = getSpendingPeriodLabel(period, currentDate),
            onPeriodChange = onPeriodChange,
            onPrevClick = onPrevClick,
            onNextClick = onNextClick
        )

        Spacer(modifier = Modifier.height(6.dp))

        GuiltyPleasureCircleChart(ui = ui)

        Spacer(modifier = Modifier.height(10.dp))

        TrendPeriodSelector(
            selected = trendPeriod,
            onSelected = { trendPeriod = it }
        )

        CategoryRatioTrendChart(
            points = trendPoints,
            lineColor = Color(0xFFE11D48)
        )

        Spacer(modifier = Modifier.height(-30.dp))

        CompareBox(
            trendPeriod = trendPeriod,
            diffPoint = diffPoint,
            positiveMessage = "기호성 식품 소비 비중이 높아졌어요.",
            negativeMessage = "기호성 식품 소비 비중이 줄어들었어요.",
            sameMessage = "기호성 식품 소비 비중이 유지되고 있어요.",
            accentColor = Color(0xFFE11D48),
            backgroundColor = Color(0xFFFFEEF1)
        )
    }
}

@Composable
private fun CategoryTrendScreen(
    receipts: List<ReceiptListUi>,
    details: List<ReceiptDetailData>,
    initialCategory: String,
    currentDate: Calendar,
    onBackClick: () -> Unit
) {
    val availableCategories = remember(details) {
        details
            .flatMap { it.items }
            .mapNotNull { it.category }
            .filter { it.isNotBlank() && it != "기타" && it != "Uncategorized" }
            .distinct()
            .sorted()
    }

    var selectedCategory by remember(initialCategory, availableCategories) {
        mutableStateOf(
            if (initialCategory in availableCategories) {
                initialCategory
            } else {
                availableCategories.firstOrNull() ?: "식재료"
            }
        )
    }

    var trendPeriod by remember { mutableStateOf(TrendPeriod.MONTHLY) }

    val points = buildCategoryAmountTrendPoints(
        receipts = receipts,
        details = details,
        category = selectedCategory,
        trendPeriod = trendPeriod,
        currentDate = currentDate
    )

    val diffAmount = if (points.size >= 2) {
        points.last().amount - points[points.lastIndex - 1].amount
    } else {
        null
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .padding(horizontal = 24.dp),
        contentPadding = PaddingValues(bottom = 92.dp)
    ) {
        item {
            Spacer(modifier = Modifier.height(38.dp))

            IconButton(
                onClick = onBackClick,
                modifier = Modifier.size(42.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.ArrowBack,
                    contentDescription = "뒤로가기",
                    tint = Color(0xFF111827),
                    modifier = Modifier.size(26.dp)
                )
            }

            Spacer(modifier = Modifier.height(18.dp))

            Text(
                text = "카테고리별 지출 추이",
                fontSize = 26.sp,
                fontWeight = FontWeight.ExtraBold,
                color = Color(0xFF0B2A6F)
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "선택한 카테고리의 지출 금액 변화를 확인할 수 있어요",
                fontSize = 15.sp,
                lineHeight = 21.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF9AA3B2)
            )

            Spacer(modifier = Modifier.height(26.dp))

            CategoryDropdown(
                categories = availableCategories,
                selectedCategory = selectedCategory,
                onCategorySelected = { selectedCategory = it }
            )

            Spacer(modifier = Modifier.height(10.dp))

            TrendPeriodSelector(
                selected = trendPeriod,
                onSelected = { trendPeriod = it }
            )

            Spacer(modifier = Modifier.height(6.dp))

            CategoryAmountTrendChart(
                points = points,
                lineColor = categoryColorByName(selectedCategory)
            )

            Spacer(modifier = Modifier.height(22.dp))

            CategoryTrendAmountCompareBox(
                category = selectedCategory,
                trendPeriod = trendPeriod,
                diffAmount = diffAmount
            )
        }
    }
}

@Composable
private fun CategoryTrendAmountCompareBox(
    category: String,
    trendPeriod: TrendPeriod,
    diffAmount: Int?
) {
    val compareLabel = when (trendPeriod) {
        TrendPeriod.WEEKLY -> "지난주"
        TrendPeriod.MONTHLY -> "지난달"
    }

    val backgroundColor = Color(0xFFEAF6FF)
    val accentColor = Color(0xFF0B74D1)

    if (diffAmount == null) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(backgroundColor)
                .padding(horizontal = 16.dp, vertical = 14.dp)
        ) {
            Text(
                text = "$compareLabel 비교 데이터가 아직 부족해요.",
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = accentColor
            )
        }
        return
    }

    val summaryText = when {
        diffAmount > 0 ->
            "${compareLabel}보다 $category 지출이 ${formatDashboardPrice(abs(diffAmount))}원 증가했어요."

        diffAmount < 0 ->
            "${compareLabel}보다 $category 지출이 ${formatDashboardPrice(abs(diffAmount))}원 감소했어요."

        else ->
            "${compareLabel}과 $category 지출이 비슷한 수준이에요."
    }

    val diffText = when {
        diffAmount > 0 -> "${formatDashboardPrice(abs(diffAmount))}원 증가"
        diffAmount < 0 -> "${formatDashboardPrice(abs(diffAmount))}원 감소"
        else -> "변화 없음"
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(backgroundColor)
            .padding(horizontal = 16.dp, vertical = 14.dp)
    ) {
        Text(
            text = summaryText,
            fontSize = 13.sp,
            fontWeight = FontWeight.Bold,
            color = accentColor
        )
    }
}
@Composable
private fun CategoryAmountTrendChart(
    points: List<TrendAmountPointUi>,
    lineColor: Color
) {
    if (points.isEmpty()) {
        EmptyAnalysisCard("추이 데이터가 없습니다.")
        return
    }

    val maxAmount = points.maxOfOrNull { it.amount } ?: 0
    val safeMax = if (maxAmount <= 0) 1 else maxAmount

    Canvas(
        modifier = Modifier
            .fillMaxWidth()
            .height(220.dp)
    ) {
        val chartLeft = 18.dp.toPx()
        val chartRight = size.width - 18.dp.toPx()
        val chartTop = 28.dp.toPx()
        val chartBottom = size.height - 48.dp.toPx()
        val chartHeight = chartBottom - chartTop

        val stepX = if (points.size > 1) {
            (chartRight - chartLeft) / (points.size - 1)
        } else {
            0f
        }

        val offsets = points.mapIndexed { index, point ->
            val x = chartLeft + stepX * index
            val ratio = point.amount.toFloat() / safeMax.toFloat()
            val y = chartBottom - (chartHeight * ratio)
            Offset(x, y)
        }

        for (i in 0 until offsets.lastIndex) {
            drawLine(
                color = lineColor,
                start = offsets[i],
                end = offsets[i + 1],
                strokeWidth = 3.dp.toPx(),
                cap = StrokeCap.Round
            )
        }

        offsets.forEachIndexed { index, offset ->
            val isCurrent = index == offsets.lastIndex

            drawCircle(
                color = lineColor,
                radius = if (isCurrent) 7.dp.toPx() else 5.dp.toPx(),
                center = offset
            )

            if (isCurrent) {
                drawCircle(
                    color = Color.White,
                    radius = 4.2.dp.toPx(),
                    center = offset
                )

                drawCircle(
                    color = lineColor,
                    radius = 2.5.dp.toPx(),
                    center = offset
                )
            }
        }

        val amountPaint = Paint().apply {
            color = android.graphics.Color.parseColor("#111827")
            textAlign = Paint.Align.CENTER
            textSize = 28f
            isFakeBoldText = true
            isAntiAlias = true
        }

        val labelPaint = Paint().apply {
            color = android.graphics.Color.parseColor("#111827")
            textAlign = Paint.Align.CENTER
            textSize = 32f
            isFakeBoldText = true
            isAntiAlias = true
        }

        offsets.forEachIndexed { index, offset ->
            val point = points[index]

            drawContext.canvas.nativeCanvas.drawText(
                "${formatDashboardPrice(point.amount)}원",
                offset.x,
                offset.y - 18.dp.toPx(),
                amountPaint
            )

            drawContext.canvas.nativeCanvas.drawText(
                point.label,
                offset.x,
                chartBottom + 42.dp.toPx(),
                labelPaint
            )
        }
    }
}

@Composable
private fun SectionTitle(
    title: String,
    description: String
) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Text(
            text = title,
            fontSize = 24.sp,
            fontWeight = FontWeight.ExtraBold,
            color = Color(0xFF0B2A6F)
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = description,
            fontSize = 15.sp,
            fontWeight = FontWeight.Medium,
            color = Color(0xFF8A93A3)
        )
    }
}

@Composable
private fun SectionDivider() {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(10.dp)
            .background(Color(0xFFF5F6F8))
    )
}

@Composable
private fun SpendingPeriodNavigator(
    selectedPeriod: TendencyPeriod,
    label: String,
    onPeriodChange: (TendencyPeriod) -> Unit,
    onPrevClick: () -> Unit,
    onNextClick: () -> Unit
) {
    var expanded by remember { mutableStateOf(false) }

    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box {
            Row(
                modifier = Modifier
                    .width(82.dp)
                    .height(42.dp)
                    .clip(RoundedCornerShape(10.dp))
                    .border(1.dp, Color(0xFFD9DEE8), RoundedCornerShape(10.dp))
                    .clickable { expanded = true }
                    .padding(horizontal = 12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = when (selectedPeriod) {
                        TendencyPeriod.DAILY -> "일간"
                        TendencyPeriod.WEEKLY -> "주간"
                        TendencyPeriod.MONTHLY -> "월간"
                    },
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF202632),
                    modifier = Modifier.weight(1f)
                )

                Icon(
                    imageVector = Icons.Default.KeyboardArrowDown,
                    contentDescription = null,
                    tint = Color(0xFF202632),
                    modifier = Modifier.size(18.dp)
                )
            }

            DropdownMenu(
                expanded = expanded,
                onDismissRequest = { expanded = false }
            ) {
                listOf(
                    TendencyPeriod.DAILY to "일간",
                    TendencyPeriod.WEEKLY to "주간",
                    TendencyPeriod.MONTHLY to "월간"
                ).forEach { (period, text) ->
                    DropdownMenuItem(
                        text = { Text(text = text) },
                        onClick = {
                            onPeriodChange(period)
                            expanded = false
                        }
                    )
                }
            }
        }

        Spacer(modifier = Modifier.width(20.dp))

        Text(
            text = "‹",
            modifier = Modifier
                .size(34.dp)
                .clickable { onPrevClick() },
            fontSize = 29.sp,
            fontWeight = FontWeight.Medium,
            color = Color(0xFF9AA3B2),
            textAlign = TextAlign.Center
        )

        Text(
            text = label,
            modifier = Modifier.weight(1f),
            fontSize = 17.sp,
            fontWeight = FontWeight.ExtraBold,
            color = Color(0xFF202632),
            textAlign = TextAlign.Center
        )

        Text(
            text = "›",
            modifier = Modifier
                .size(34.dp)
                .clickable { onNextClick() },
            fontSize = 29.sp,
            fontWeight = FontWeight.Medium,
            color = Color(0xFF9AA3B2),
            textAlign = TextAlign.Center
        )
    }
}

@Composable
private fun CategoryDropdown(
    categories: List<String>,
    selectedCategory: String,
    onCategorySelected: (String) -> Unit
) {
    var expanded by remember { mutableStateOf(false) }

    Box {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(44.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(Color(0xFFF7F8FC))
                .border(1.dp, Color(0xFFE5E7EB), RoundedCornerShape(12.dp))
                .clickable { expanded = true }
                .padding(horizontal = 14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(9.dp)
                    .clip(CircleShape)
                    .background(categoryColorByName(selectedCategory))
            )

            Spacer(modifier = Modifier.width(10.dp))

            Text(
                text = selectedCategory,
                fontSize = 14.sp,
                fontWeight = FontWeight.ExtraBold,
                color = Color(0xFF111827),
                modifier = Modifier.weight(1f)
            )

            Icon(
                imageVector = Icons.Default.KeyboardArrowDown,
                contentDescription = null,
                tint = Color(0xFF111827),
                modifier = Modifier.size(18.dp)
            )
        }

        DropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false }
        ) {
            categories.forEach { category ->
                DropdownMenuItem(
                    text = { Text(text = category, fontSize = 13.sp) },
                    onClick = {
                        onCategorySelected(category)
                        expanded = false
                    }
                )
            }
        }
    }
}

@Composable
private fun CategoryDonutChart(
    categories: List<CategorySpendingUi>,
    topCategory: CategorySpendingUi?
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(214.dp),
        contentAlignment = Alignment.Center
    ) {
        Canvas(modifier = Modifier.size(130.dp)) {
            val normalStroke = 37.dp.toPx()
            val highlightStroke = 46.dp.toPx()
            val gap = 3.0f
            var startAngle = -90f

            categories.forEach { category ->
                val sweep = (category.percent / 100.0 * 360.0).toFloat()
                val isTop = category.name == topCategory?.name

                drawArc(
                    color = categoryColorByName(category.name),
                    startAngle = startAngle + gap / 2f,
                    sweepAngle = (sweep - gap).coerceAtLeast(0f),
                    useCenter = false,
                    topLeft = Offset(
                        if (isTop) -4.dp.toPx() else 0f,
                        if (isTop) -4.dp.toPx() else 0f
                    ),
                    size = Size(
                        width = size.width + if (isTop) 8.dp.toPx() else 0f,
                        height = size.height + if (isTop) 8.dp.toPx() else 0f
                    ),
                    style = Stroke(
                        width = if (isTop) highlightStroke else normalStroke,
                        cap = StrokeCap.Butt
                    )
                )

                startAngle += sweep
            }
        }

        if (topCategory != null) {
            Surface(
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .offset(x = (-22).dp, y = 34.dp),
                shape = CircleShape,
                color = Color.White,
                shadowElevation = 7.dp
            ) {
                Column(
                    modifier = Modifier
                        .size(76.dp)
                        .padding(top = 15.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = topCategory.name,
                        fontSize = 11.5.sp,
                        fontWeight = FontWeight.ExtraBold,
                        color = Color(0xFF4B5563)
                    )

                    Text(
                        text = "${topCategory.percent.toInt()}%",
                        fontSize = 19.sp,
                        fontWeight = FontWeight.ExtraBold,
                        color = categoryColorByName(topCategory.name)
                    )
                }
            }
        }
    }
}

@Composable
private fun SpendingTotalRow(totalPayment: Int) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = "전체",
            fontSize = 13.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFFA0A7B5),
            modifier = Modifier.weight(1f)
        )

        Text(
            text = "${formatDashboardPrice(totalPayment)}원",
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFFA0A7B5)
        )
    }
}

@Composable
private fun CategorySpendingRow(
    category: CategorySpendingUi
) {
    val color = categoryColorByName(category.name)

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(28.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(9.dp)
                .clip(CircleShape)
                .background(color)
        )

        Spacer(modifier = Modifier.width(12.dp))

        Text(
            text = category.name,
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF202632)
        )

        Spacer(modifier = Modifier.width(6.dp))

        Text(
            text = "${category.percent.toInt()}%",
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFFA0A7B5),
            modifier = Modifier.weight(1f)
        )

        Text(
            text = "${formatDashboardPrice(category.amount)}원",
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF202632)
        )
    }
}

@Composable
private fun HomeCookingGauge(ui: HomeCookingUi) {
    val percent = (ui.ratio * 100.0).coerceIn(0.0, 100.0)
    val ingredientColor = Color(0xFF17A99B)
    val convenienceColor = Color(0xFFDDE8EF)

    Column(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "식재료",
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF202632)
            )

            Spacer(modifier = Modifier.width(10.dp))

            Box(
                modifier = Modifier
                    .weight(1f)
                    .padding(horizontal = 2.dp)
                    .height(42.dp)
                    .clip(RoundedCornerShape(3.dp))
                    .background(convenienceColor)
                    .border(1.dp, Color(0xFFD2DCE8), RoundedCornerShape(3.dp))
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxHeight()
                        .fillMaxWidth((percent / 100.0).toFloat())
                        .background(ingredientColor)
                )

                Box(
                    modifier = Modifier
                        .align(Alignment.Center)
                        .width(1.dp)
                        .fillMaxHeight()
                        .background(Color(0xFFD1D5DB))
                )
            }

            Spacer(modifier = Modifier.width(10.dp))

            Text(
                text = "간편식",
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF202632)
            )
        }

        Spacer(modifier = Modifier.height(7.dp))

        Text(
            text = "${formatTendencyPercent(percent)}%",
            modifier = Modifier.fillMaxWidth(),
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            color = ingredientColor,
            textAlign = TextAlign.Center
        )
    }
}

@Composable
private fun HomeCookingAmountBox(ui: HomeCookingUi) {
    Column(
        modifier = Modifier.fillMaxWidth()
    ) {
        HomeCookingAmountRow(
            label = "전체",
            amount = ui.totalAmount,
            labelColor = Color(0xFF9AA3B2)
        )

        Spacer(modifier = Modifier.height(10.dp))

        Divider(color = Color(0xFFE5E7EB), thickness = 1.dp)

        Spacer(modifier = Modifier.height(14.dp))

        HomeCookingAmountRow(
            label = "식재료",
            amount = ui.ingredientAmount,
            labelColor = Color(0xFF0F766E)
        )

        Spacer(modifier = Modifier.height(14.dp))

        HomeCookingAmountRow(
            label = "간편식",
            amount = ui.convenienceAmount,
            labelColor = Color(0xFF9AA3B2)
        )
    }
}

@Composable
private fun HomeCookingAmountRow(
    label: String,
    amount: Int,
    labelColor: Color
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = label,
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
            color = labelColor,
            modifier = Modifier.weight(1f)
        )

        Text(
            text = "${formatDashboardPrice(amount)}원",
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF111827)
        )
    }
}

@Composable
private fun GuiltyPleasureCircleChart(
    ui: GuiltyPleasureUi
) {
    val percent = (ui.ratio * 100.0).coerceIn(0.0, 100.0)
    val sweepAngle = (percent / 100.0 * 360.0).toFloat()

    val accentColor = Color(0xFFE73563)
    val trackColor = Color(0xFFE9EDF3)

    Column(
        modifier = Modifier.fillMaxWidth()
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(185.dp),
            contentAlignment = Alignment.Center
        ) {
            Canvas(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(175.dp)
            ) {
                val circleSize = 145.dp.toPx()
                val left = 14.dp.toPx()
                val top = 8.dp.toPx()

                drawArc(
                    color = trackColor,
                    startAngle = -90f,
                    sweepAngle = 360f,
                    useCenter = true,
                    topLeft = androidx.compose.ui.geometry.Offset(left, top),
                    size = Size(circleSize, circleSize)
                )

                if (sweepAngle > 0f) {
                    drawArc(
                        color = accentColor,
                        startAngle = -90f,
                        sweepAngle = sweepAngle,
                        useCenter = true,
                        topLeft = androidx.compose.ui.geometry.Offset(left, top),
                        size = Size(circleSize, circleSize)
                    )
                }

                val centerX = left + circleSize / 2f
                val centerY = top + circleSize / 2f

                val radius = circleSize / 2f

                val sliceMiddleAngle = -90f + (sweepAngle / 2f)
                val sliceMiddleRadian = Math.toRadians(sliceMiddleAngle.toDouble())

                val lineStart = androidx.compose.ui.geometry.Offset(
                    x = centerX + kotlin.math.cos(sliceMiddleRadian).toFloat() * radius * 0.72f,
                    y = centerY + kotlin.math.sin(sliceMiddleRadian).toFloat() * radius * 0.72f
                )

                val lineEnd = androidx.compose.ui.geometry.Offset(
                    x = size.width - 68.dp.toPx(),
                    y = centerY - 24.dp.toPx()
                )

                drawLine(
                    color = accentColor,
                    start = lineStart,
                    end = lineEnd,
                    strokeWidth = 1.4.dp.toPx()
                )
            }

            Column(
                modifier = Modifier
                    .align(Alignment.CenterEnd)
                    .offset(y = (-18).dp)
                    .padding(end = 4.dp),
                horizontalAlignment = Alignment.Start
            ) {
                Text(
                    text = "간식·주류",
                    fontSize = 15.sp,
                    fontWeight = FontWeight.ExtraBold,
                    color = Color(0xFF111827)
                )

                Text(
                    text = "${formatTendencyPercent(percent)}%",
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Bold,
                    color = accentColor
                )
            }
        }

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 1.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "전체",
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF8A93A3),
                modifier = Modifier.weight(1f)
            )

            Text(
                text = "${formatPrice(ui.totalPayment)}원",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF8A93A3)
            )
        }

        Spacer(modifier = Modifier.height(4.dp))

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(1.dp)
                .background(Color(0xFFE5E7EB))
        )

        Spacer(modifier = Modifier.height(6.dp))

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 2.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "간식·주류",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF111827),
                modifier = Modifier.weight(1f)
            )

            Text(
                text = "${formatPrice(ui.guiltyAmount)}원",
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF111827)
            )
        }
    }
}

@Composable
private fun TrendPeriodSelector(
    selected: TrendPeriod,
    onSelected: (TrendPeriod) -> Unit
) {
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        TrendPeriodButton(
            text = "월별",
            selected = selected == TrendPeriod.MONTHLY,
            onClick = { onSelected(TrendPeriod.MONTHLY) }
        )

        TrendPeriodButton(
            text = "주별",
            selected = selected == TrendPeriod.WEEKLY,
            onClick = { onSelected(TrendPeriod.WEEKLY) }
        )
    }
}

@Composable
private fun TrendPeriodButton(
    text: String,
    selected: Boolean,
    onClick: () -> Unit
) {
    Box(
        modifier = Modifier
            .height(34.dp)
            .clip(RoundedCornerShape(9.dp))
            .border(
                width = 1.dp,
                color = if (selected) Color(0xFF111827) else Color(0xFFD7DCE5),
                shape = RoundedCornerShape(9.dp)
            )
            .background(if (selected) Color.White else Color(0xFFF9FAFB))
            .clickable { onClick() }
            .padding(horizontal = 13.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = text,
            fontSize = 12.5.sp,
            fontWeight = FontWeight.ExtraBold,
            color = if (selected) Color(0xFF111827) else Color(0xFF9AA3B2)
        )
    }
}

@Composable
private fun RatioTrendChart(
    points: List<TrendRatioPointUi>,
    lineColor: Color,
    yLabel: String
) {
    if (points.isEmpty()) return

    Column(modifier = Modifier.fillMaxWidth()) {
        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(50.dp)
        ) {
            val leftPadding = 44.dp.toPx()
            val rightPadding = 16.dp.toPx()
            val topPadding = 16.dp.toPx()
            val bottomPadding = 34.dp.toPx()

            val chartWidth = size.width - leftPadding - rightPadding
            val chartHeight = size.height - topPadding - bottomPadding
            val axisColor = Color(0xFF111827)
            val gridColor = Color(0xFFE8ECF2)

            listOf(0f, 0.5f, 1f).forEach { ratio ->
                val y = topPadding + chartHeight - chartHeight * ratio
                drawLine(
                    color = gridColor,
                    start = Offset(leftPadding, y),
                    end = Offset(leftPadding + chartWidth, y),
                    strokeWidth = 1.dp.toPx()
                )
            }

            drawLine(
                color = axisColor,
                start = Offset(leftPadding, topPadding),
                end = Offset(leftPadding, topPadding + chartHeight),
                strokeWidth = 2.dp.toPx()
            )
            drawLine(
                color = axisColor,
                start = Offset(leftPadding, topPadding + chartHeight),
                end = Offset(leftPadding + chartWidth, topPadding + chartHeight),
                strokeWidth = 2.dp.toPx()
            )

            val stepX = if (points.size > 1) chartWidth / (points.size - 1) else 0f
            val offsets = points.mapIndexed { index, point ->
                val x = leftPadding + stepX * index
                val y = topPadding + chartHeight -
                        (point.ratio.coerceIn(0.0, 1.0).toFloat() * chartHeight)
                Offset(x, y)
            }

            offsets.zipWithNext().forEach { (start, end) ->
                drawLine(
                    color = lineColor,
                    start = start,
                    end = end,
                    strokeWidth = 2.6.dp.toPx(),
                    cap = StrokeCap.Round
                )
            }

            offsets.forEach { point ->
                drawCircle(
                    color = lineColor,
                    radius = 4.2.dp.toPx(),
                    center = point
                )
                drawCircle(
                    color = Color.White,
                    radius = 2.1.dp.toPx(),
                    center = point
                )
            }
        }

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(start = 44.dp, end = 16.dp)
        ) {
            points.forEach { point ->
                Text(
                    text = point.label,
                    fontSize = 10.5.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF8A93A3),
                    textAlign = TextAlign.Center,
                    modifier = Modifier.weight(1f)
                )
            }
        }

        Spacer(modifier = Modifier.height(2.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(
                modifier = Modifier.width(42.dp),
                horizontalAlignment = Alignment.End
            ) {
                Text("100%", fontSize = 10.5.sp, fontWeight = FontWeight.Bold, color = Color(0xFF6B7280))
                Spacer(modifier = Modifier.height(48.dp))
                Text("50%", fontSize = 10.5.sp, fontWeight = FontWeight.Bold, color = Color(0xFF9AA3B2))
                Spacer(modifier = Modifier.height(48.dp))
                Text("0%", fontSize = 10.5.sp, fontWeight = FontWeight.Bold, color = Color(0xFF6B7280))
            }
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = yLabel,
                fontSize = 12.sp,
                fontWeight = FontWeight.ExtraBold,
                color = Color(0xFF111827)
            )
        }
    }
}

@Composable
private fun AmountTrendChart(
    points: List<TrendAmountPointUi>,
    lineColor: Color,
    yLabel: String
) {
    if (points.isEmpty()) return

    val maxAmount = roundUpAmount(points.maxOfOrNull { it.amount } ?: 0)
    val safeMax = maxAmount.coerceAtLeast(1)

    Column(modifier = Modifier.fillMaxWidth()) {
        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(190.dp)
        ) {
            val leftPadding = 44.dp.toPx()
            val rightPadding = 16.dp.toPx()
            val topPadding = 16.dp.toPx()
            val bottomPadding = 34.dp.toPx()

            val chartWidth = size.width - leftPadding - rightPadding
            val chartHeight = size.height - topPadding - bottomPadding
            val axisColor = Color(0xFF111827)
            val gridColor = Color(0xFFE8ECF2)

            listOf(0f, 0.5f, 1f).forEach { ratio ->
                val y = topPadding + chartHeight - chartHeight * ratio
                drawLine(
                    color = gridColor,
                    start = Offset(leftPadding, y),
                    end = Offset(leftPadding + chartWidth, y),
                    strokeWidth = 1.dp.toPx()
                )
            }

            drawLine(
                color = axisColor,
                start = Offset(leftPadding, topPadding),
                end = Offset(leftPadding, topPadding + chartHeight),
                strokeWidth = 2.dp.toPx()
            )
            drawLine(
                color = axisColor,
                start = Offset(leftPadding, topPadding + chartHeight),
                end = Offset(leftPadding + chartWidth, topPadding + chartHeight),
                strokeWidth = 2.dp.toPx()
            )

            val stepX = if (points.size > 1) chartWidth / (points.size - 1) else 0f
            val offsets = points.mapIndexed { index, point ->
                val x = leftPadding + stepX * index
                val y = topPadding + chartHeight -
                        ((point.amount.toFloat() / safeMax.toFloat()).coerceIn(0f, 1f) * chartHeight)
                Offset(x, y)
            }

            offsets.zipWithNext().forEach { (start, end) ->
                drawLine(
                    color = lineColor,
                    start = start,
                    end = end,
                    strokeWidth = 2.6.dp.toPx(),
                    cap = StrokeCap.Round
                )
            }

            offsets.forEach { point ->
                drawCircle(color = lineColor, radius = 4.2.dp.toPx(), center = point)
                drawCircle(color = Color.White, radius = 2.1.dp.toPx(), center = point)
            }
        }

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(start = 44.dp, end = 16.dp)
        ) {
            points.forEach { point ->
                Text(
                    text = point.label,
                    fontSize = 10.5.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF8A93A3),
                    textAlign = TextAlign.Center,
                    modifier = Modifier.weight(1f)
                )
            }
        }

        Spacer(modifier = Modifier.height(2.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(
                modifier = Modifier.width(42.dp),
                horizontalAlignment = Alignment.End
            ) {
                Text("${formatShortPrice(safeMax)}", fontSize = 10.5.sp, fontWeight = FontWeight.Bold, color = Color(0xFF6B7280))
                Spacer(modifier = Modifier.height(48.dp))
                Text("${formatShortPrice(safeMax / 2)}", fontSize = 10.5.sp, fontWeight = FontWeight.Bold, color = Color(0xFF9AA3B2))
                Spacer(modifier = Modifier.height(48.dp))
                Text("0원", fontSize = 10.5.sp, fontWeight = FontWeight.Bold, color = Color(0xFF6B7280))
            }
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = yLabel,
                fontSize = 12.sp,
                fontWeight = FontWeight.ExtraBold,
                color = Color(0xFF111827)
            )
        }
    }
}

@Composable
private fun CompareBox(
    trendPeriod: TrendPeriod,
    diffPoint: Double?,
    positiveMessage: String,
    negativeMessage: String,
    sameMessage: String,
    accentColor: Color,
    backgroundColor: Color
) {
    val compareLabel = when (trendPeriod) {
        TrendPeriod.WEEKLY -> "지난주"
        TrendPeriod.MONTHLY -> "지난달"
    }

    if (diffPoint == null) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(backgroundColor)
                .padding(horizontal = 16.dp, vertical = 13.dp)
        ) {
            Text(
                text = "$compareLabel 비교 데이터가 아직 부족해요.",
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = accentColor
            )
        }
        return
    }

    val sign = when {
        diffPoint > 0 -> "+"
        diffPoint < 0 -> "-"
        else -> ""
    }

    val message = when {
        diffPoint > 0 -> positiveMessage
        diffPoint < 0 -> negativeMessage
        else -> sameMessage
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(backgroundColor)
            .padding(horizontal = 16.dp, vertical = 13.dp)
    ) {
        Text(
            text = "$compareLabel 대비 $sign${formatTendencyPercent(abs(diffPoint))}%p",
            fontSize = 13.sp,
            fontWeight = FontWeight.Bold,
            color = accentColor
        )

        Spacer(modifier = Modifier.height(4.dp))

        Text(
            text = message,
            fontSize = 13.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF4B5563)
        )
    }
}

@Composable
private fun EmptyAnalysisCard(message: String) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        color = Color.White,
        shadowElevation = 1.dp
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(130.dp)
                .padding(18.dp),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = message,
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF8A93A3),
                textAlign = TextAlign.Center
            )
        }
    }
}

@Composable
private fun CategoryEditScreen(
    detail: ReceiptDetailData,
    isSaving: Boolean,
    onBackClick: () -> Unit,
    onSaveClick: (Map<Int, String>) -> Unit
) {
    var selectedCategories by remember(detail.receipt_id) {
        mutableStateOf(
            detail.items
                .mapNotNull { item ->
                    item.id?.let { id ->
                        id to (item.category ?: "Uncategorized")
                    }
                }
                .toMap()
        )
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .padding(horizontal = 18.dp)
    ) {
        Spacer(modifier = Modifier.height(26.dp))

        Box(
            modifier = Modifier.fillMaxWidth(),
            contentAlignment = Alignment.Center
        ) {
            IconButton(
                onClick = onBackClick,
                modifier = Modifier.align(Alignment.CenterStart)
            ) {
                Icon(
                    imageVector = Icons.Default.ArrowBack,
                    contentDescription = "뒤로가기",
                    tint = Color(0xFF111827)
                )
            }

            Text(
                text = "카테고리 구성",
                fontSize = 22.sp,
                fontWeight = FontWeight.ExtraBold,
                color = Color(0xFF111827)
            )
        }

        Spacer(modifier = Modifier.height(22.dp))

        LazyColumn(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            contentPadding = PaddingValues(bottom = 20.dp)
        ) {
            items(detail.items.size) { index ->
                val item = detail.items[index]
                val itemId = item.id

                if (itemId != null) {
                    CategoryEditRow(
                        itemName = item.name ?: "상품명 없음",
                        selectedCategory = selectedCategories[itemId] ?: "Uncategorized",
                        onCategorySelected = { category ->
                            selectedCategories = selectedCategories.toMutableMap().apply {
                                put(itemId, category)
                            }
                        }
                    )
                }
            }
        }

        Button(
            onClick = { onSaveClick(selectedCategories) },
            enabled = !isSaving,
            modifier = Modifier
                .fillMaxWidth()
                .height(58.dp),
            shape = RoundedCornerShape(14.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = Color(0xFF1769FF),
                contentColor = Color.White
            )
        ) {
            if (isSaving) {
                CircularProgressIndicator(
                    modifier = Modifier.size(22.dp),
                    strokeWidth = 2.dp,
                    color = Color.White
                )
            } else {
                Text(
                    text = "저장하기",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }

        Spacer(modifier = Modifier.height(22.dp))
    }
}

@Composable
private fun CategoryEditRow(
    itemName: String,
    selectedCategory: String,
    onCategorySelected: (String) -> Unit
) {
    var expanded by remember { mutableStateOf(false) }

    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        color = Color.White,
        shadowElevation = 2.dp
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = itemName,
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF111827),
                modifier = Modifier.weight(1f),
                maxLines = 2
            )

            Spacer(modifier = Modifier.width(12.dp))

            Box {
                Row(
                    modifier = Modifier
                        .width(132.dp)
                        .height(42.dp)
                        .clip(RoundedCornerShape(12.dp))
                        .background(Color(0xFFF7F8FC))
                        .border(
                            width = 1.dp,
                            color = Color(0xFFE5E7EB),
                            shape = RoundedCornerShape(12.dp)
                        )
                        .clickable { expanded = true }
                        .padding(horizontal = 10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = selectedCategory,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF111827),
                        modifier = Modifier.weight(1f),
                        maxLines = 1
                    )

                    Icon(
                        imageVector = Icons.Default.KeyboardArrowDown,
                        contentDescription = "카테고리 선택",
                        tint = Color(0xFF111827),
                        modifier = Modifier.size(20.dp)
                    )
                }

                DropdownMenu(
                    expanded = expanded,
                    onDismissRequest = { expanded = false }
                ) {
                    AllowedCategories.forEach { category ->
                        DropdownMenuItem(
                            text = { Text(text = category, fontSize = 13.sp) },
                            onClick = {
                                onCategorySelected(category)
                                expanded = false
                            }
                        )
                    }
                }
            }
        }
    }
}

private fun buildCategorySpendingUi(
    details: List<ReceiptDetailData>,
    totalPayment: Int
): List<CategorySpendingUi> {
    val grouped = details
        .flatMap { it.items }
        .filter { item ->
            val category = item.category
            !category.isNullOrBlank() && category != "Uncategorized"
        }
        .groupBy { it.category ?: "기타" }

    return grouped.map { (category, items) ->
        val amount = items.sumOf { it.final_price ?: 0 }

        CategorySpendingUi(
            name = category,
            amount = amount,
            percent = if (totalPayment > 0) amount * 100.0 / totalPayment else 0.0
        )
    }
        .filter { it.amount > 0 }
        .sortedWith(
            compareBy<CategorySpendingUi> { if (it.name == "기타") 1 else 0 }
                .thenByDescending { it.amount }
        )
}

private fun buildHomeCookingUi(details: List<ReceiptDetailData>): HomeCookingUi {
    val ingredientAmount = details.sumOf { detail ->
        sumCategoryAmountForTendency(detail.items, setOf("식재료"))
    }

    val convenienceAmount = details.sumOf { detail ->
        sumCategoryAmountForTendency(detail.items, setOf("간편식"))
    }

    val totalAmount = ingredientAmount + convenienceAmount

    return HomeCookingUi(
        ingredientAmount = ingredientAmount,
        convenienceAmount = convenienceAmount,
        totalAmount = totalAmount,
        ratio = if (totalAmount > 0) ingredientAmount.toDouble() / totalAmount else 0.0
    )
}

private fun buildGuiltyPleasureUi(details: List<ReceiptDetailData>): GuiltyPleasureUi {
    val guiltyAmount = details.sumOf { detail ->
        sumCategoryAmountForTendency(detail.items, setOf("간식", "주류"))
    }

    val totalPayment = details.sumOf { detail ->
        detail.items.sumOf { item -> item.final_price ?: 0 }
    }

    return GuiltyPleasureUi(
        guiltyAmount = guiltyAmount,
        totalPayment = totalPayment,
        ratio = if (totalPayment > 0) guiltyAmount.toDouble() / totalPayment else 0.0
    )
}

private fun buildPreviousHomeCookingUi(
    receipts: List<ReceiptListUi>,
    details: List<ReceiptDetailData>,
    trendPeriod: TrendPeriod,
    currentDate: Calendar
): HomeCookingUi? {
    val previousDate = currentDate.clone() as Calendar
    when (trendPeriod) {
        TrendPeriod.WEEKLY -> previousDate.add(Calendar.WEEK_OF_YEAR, -1)
        TrendPeriod.MONTHLY -> previousDate.add(Calendar.MONTH, -1)
    }

    val previousDetails = getDetailsInPeriod(
        receipts = receipts,
        details = details,
        period = trendPeriod.toTendencyPeriod(),
        currentDate = previousDate
    )

    if (previousDetails.isEmpty()) return null
    return buildHomeCookingUi(previousDetails)
}

private fun buildPreviousGuiltyPleasureUi(
    receipts: List<ReceiptListUi>,
    details: List<ReceiptDetailData>,
    trendPeriod: TrendPeriod,
    currentDate: Calendar
): GuiltyPleasureUi? {
    val previousDate = currentDate.clone() as Calendar
    when (trendPeriod) {
        TrendPeriod.WEEKLY -> previousDate.add(Calendar.WEEK_OF_YEAR, -1)
        TrendPeriod.MONTHLY -> previousDate.add(Calendar.MONTH, -1)
    }

    val previousDetails = getDetailsInPeriod(
        receipts = receipts,
        details = details,
        period = trendPeriod.toTendencyPeriod(),
        currentDate = previousDate
    )

    if (previousDetails.isEmpty()) return null
    return buildGuiltyPleasureUi(previousDetails)
}

private fun buildHomeCookingTrendPoints(
    receipts: List<ReceiptListUi>,
    details: List<ReceiptDetailData>,
    trendPeriod: TrendPeriod,
    currentDate: Calendar
): List<TrendRatioPointUi> {
    return buildRatioTrendPoints(
        receipts = receipts,
        details = details,
        trendPeriod = trendPeriod,
        currentDate = currentDate
    ) { targetDetails ->
        buildHomeCookingUi(targetDetails).ratio
    }
}

private fun buildGuiltyPleasureTrendPoints(
    receipts: List<ReceiptListUi>,
    details: List<ReceiptDetailData>,
    trendPeriod: TrendPeriod,
    currentDate: Calendar
): List<TrendRatioPointUi> {
    return buildRatioTrendPoints(
        receipts = receipts,
        details = details,
        trendPeriod = trendPeriod,
        currentDate = currentDate
    ) { targetDetails ->
        buildGuiltyPleasureUi(targetDetails).ratio
    }
}

private fun buildRatioTrendPoints(
    receipts: List<ReceiptListUi>,
    details: List<ReceiptDetailData>,
    trendPeriod: TrendPeriod,
    currentDate: Calendar,
    ratioBuilder: (List<ReceiptDetailData>) -> Double
): List<TrendRatioPointUi> {
    val result = mutableListOf<TrendRatioPointUi>()

    for (i in 4 downTo 0) {
        val targetDate = currentDate.clone() as Calendar
        when (trendPeriod) {
            TrendPeriod.WEEKLY -> targetDate.add(Calendar.WEEK_OF_YEAR, -i)
            TrendPeriod.MONTHLY -> targetDate.add(Calendar.MONTH, -i)
        }

        val targetDetails = getDetailsInPeriod(
            receipts = receipts,
            details = details,
            period = trendPeriod.toTendencyPeriod(),
            currentDate = targetDate
        )

        result.add(
            TrendRatioPointUi(
                label = getTrendPointLabel(trendPeriod, targetDate),
                ratio = ratioBuilder(targetDetails)
            )
        )
    }

    return result
}

@Composable
private fun CategoryRatioTrendChart(
    points: List<TrendRatioPointUi>,
    lineColor: Color
) {
    if (points.isEmpty()) return

    Canvas(
        modifier = Modifier
            .fillMaxWidth()
            .height(230.dp)
    ) {
        val sidePadding = 22.dp.toPx()
        val topPadding = 44.dp.toPx()
        val bottomPadding = 72.dp.toPx()

        val chartWidth = size.width - sidePadding * 2
        val chartHeight = size.height - topPadding - bottomPadding
        val baseY = topPadding + chartHeight

        val stepX = if (points.size > 1) {
            chartWidth / (points.size - 1)
        } else {
            0f
        }

        val offsets = points.mapIndexed { index, point ->
            val x = sidePadding + stepX * index
            val y = topPadding + chartHeight -
                    (point.ratio.coerceIn(0.0, 1.0).toFloat() * chartHeight)

            Offset(x, y)
        }

        drawLine(
            color = Color(0xFF111827),
            start = Offset(sidePadding, baseY),
            end = Offset(sidePadding + chartWidth, baseY),
            strokeWidth = 2.dp.toPx(),
            cap = StrokeCap.Round
        )

        offsets.zipWithNext().forEach { (start, end) ->
            drawLine(
                color = lineColor,
                start = start,
                end = end,
                strokeWidth = 3.dp.toPx(),
                cap = StrokeCap.Round
            )
        }

        offsets.forEachIndexed { index, offset ->
            val isCurrent = index == offsets.lastIndex

            drawCircle(
                color = lineColor,
                radius = if (isCurrent) 7.dp.toPx() else 5.dp.toPx(),
                center = offset
            )

            if (isCurrent) {
                drawCircle(
                    color = Color.White,
                    radius = 4.2.dp.toPx(),
                    center = offset
                )

                drawCircle(
                    color = lineColor,
                    radius = 2.5.dp.toPx(),
                    center = offset
                )
            }
        }

        val percentPaint = Paint().apply {
            color = android.graphics.Color.parseColor("#0B7A22")
            textAlign = Paint.Align.CENTER
            textSize = 30f
            isFakeBoldText = true
            isAntiAlias = true
        }

        val labelPaint = Paint().apply {
            color = android.graphics.Color.parseColor("#111827")
            textAlign = Paint.Align.CENTER
            textSize = 32f
            isFakeBoldText = true
            isAntiAlias = true
        }

        offsets.forEachIndexed { index, offset ->
            val point = points[index]

            drawContext.canvas.nativeCanvas.drawText(
                "${(point.ratio * 100).toInt()}%",
                offset.x,
                offset.y - 18.dp.toPx(),
                percentPaint
            )

            drawContext.canvas.nativeCanvas.drawText(
                point.label,
                offset.x,
                baseY + 42.dp.toPx(),
                labelPaint
            )
        }
    }
}

@Composable
private fun CategoryTrendCompareBox(
    category: String,
    trendPeriod: TrendPeriod,
    diffPoint: Double?
) {
    val compareLabel = when (trendPeriod) {
        TrendPeriod.WEEKLY -> "지난주"
        TrendPeriod.MONTHLY -> "지난달"
    }

    val backgroundColor = Color(0xFFEAF6FF)
    val accentColor = Color(0xFF0B74D1)

    if (diffPoint == null) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(backgroundColor)
                .padding(horizontal = 16.dp, vertical = 14.dp)
        ) {
            Text(
                text = "$compareLabel 비교 데이터가 아직 부족해요.",
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = accentColor
            )
        }
        return
    }

    val sign = when {
        diffPoint > 0 -> "+"
        diffPoint < 0 -> "-"
        else -> ""
    }

    val message = when {
        diffPoint > 0 -> "$category 소비 비중이 늘어났어요."
        diffPoint < 0 -> "$category 소비 비중이 줄어들었어요."
        else -> "$category 소비 비중은 유지하는 중이에요."
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(backgroundColor)
            .padding(horizontal = 16.dp, vertical = 14.dp)
    ) {
        Text(
            text = "$compareLabel 대비 $sign${formatTendencyPercent(abs(diffPoint))}%p",
            fontSize = 13.sp,
            fontWeight = FontWeight.Bold,
            color = accentColor
        )

        Spacer(modifier = Modifier.height(5.dp))

        Text(
            text = message,
            fontSize = 13.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF374151)
        )
    }
}

private fun buildCategoryRatioTrendPoints(
    receipts: List<ReceiptListUi>,
    details: List<ReceiptDetailData>,
    category: String,
    trendPeriod: TrendPeriod,
    currentDate: Calendar
): List<TrendRatioPointUi> {
    return buildRatioTrendPoints(
        receipts = receipts,
        details = details,
        trendPeriod = trendPeriod,
        currentDate = currentDate
    ) { targetDetails ->
        val totalPayment = targetDetails.sumOf { detail ->
            detail.items.sumOf { item -> item.final_price ?: 0 }
        }

        val categoryAmount = targetDetails.sumOf { detail ->
            sumCategoryAmountForTendency(detail.items, setOf(category))
        }

        if (totalPayment > 0) {
            categoryAmount.toDouble() / totalPayment.toDouble()
        } else {
            0.0
        }
    }
}

private fun buildCategoryAmountTrendPoints(
    receipts: List<ReceiptListUi>,
    details: List<ReceiptDetailData>,
    category: String,
    trendPeriod: TrendPeriod,
    currentDate: Calendar
): List<TrendAmountPointUi> {
    val result = mutableListOf<TrendAmountPointUi>()

    for (i in 4 downTo 0) {
        val targetDate = currentDate.clone() as Calendar
        when (trendPeriod) {
            TrendPeriod.WEEKLY -> targetDate.add(Calendar.WEEK_OF_YEAR, -i)
            TrendPeriod.MONTHLY -> targetDate.add(Calendar.MONTH, -i)
        }

        val targetDetails = getDetailsInPeriod(
            receipts = receipts,
            details = details,
            period = trendPeriod.toTendencyPeriod(),
            currentDate = targetDate
        )

        val amount = targetDetails.sumOf { detail ->
            sumCategoryAmountForTendency(detail.items, setOf(category))
        }

        result.add(
            TrendAmountPointUi(
                label = getTrendPointLabel(trendPeriod, targetDate),
                amount = amount
            )
        )
    }

    return result
}

private fun getDetailsInPeriod(
    receipts: List<ReceiptListUi>,
    details: List<ReceiptDetailData>,
    period: TendencyPeriod,
    currentDate: Calendar
): List<ReceiptDetailData> {
    val targetReceiptIds = receipts
        .filter { receipt ->
            val date = parseCalendarForTendency(receipt.analyzedAtText)
            date != null && isInTendencyPeriod(date, currentDate, period)
        }
        .map { it.id }
        .toSet()

    return details.filter { it.receipt_id in targetReceiptIds }
}

private fun sumCategoryAmountForTendency(
    items: List<ReceiptDetailItemData>,
    categories: Set<String>
): Int {
    return items
        .filter { item -> item.category in categories }
        .sumOf { item -> item.final_price ?: 0 }
}

private fun TrendPeriod.toTendencyPeriod(): TendencyPeriod {
    return when (this) {
        TrendPeriod.WEEKLY -> TendencyPeriod.WEEKLY
        TrendPeriod.MONTHLY -> TendencyPeriod.MONTHLY
    }
}

private fun isInTendencyPeriod(
    date: Calendar,
    targetDate: Calendar,
    period: TendencyPeriod
): Boolean {
    return when (period) {
        TendencyPeriod.DAILY -> isSameDayForTendency(date, targetDate)
        TendencyPeriod.WEEKLY -> {
            val week = getMondayToSundayForTendency(targetDate)
            !date.before(week.first) && !date.after(week.second)
        }
        TendencyPeriod.MONTHLY -> {
            date.get(Calendar.YEAR) == targetDate.get(Calendar.YEAR) &&
                    date.get(Calendar.MONTH) == targetDate.get(Calendar.MONTH)
        }
    }
}

private fun getSpendingPeriodLabel(
    period: TendencyPeriod,
    date: Calendar
): String {
    return when (period) {
        TendencyPeriod.DAILY -> SimpleDateFormat("MM.dd", Locale.KOREA).format(date.time)
        TendencyPeriod.WEEKLY -> {
            val week = getMondayToSundayForTendency(date)
            val formatter = SimpleDateFormat("MM.dd", Locale.KOREA)
            "${formatter.format(week.first.time)} - ${formatter.format(week.second.time)}"
        }
        TendencyPeriod.MONTHLY -> {
            val start = date.clone() as Calendar
            start.set(Calendar.DAY_OF_MONTH, 1)
            val end = date.clone() as Calendar
            end.set(Calendar.DAY_OF_MONTH, end.getActualMaximum(Calendar.DAY_OF_MONTH))
            val formatter = SimpleDateFormat("MM.dd", Locale.KOREA)
            "${formatter.format(start.time)} - ${formatter.format(end.time)}"
        }
    }
}

private fun moveTendencyDate(
    current: Calendar,
    period: TendencyPeriod,
    amount: Int
): Calendar {
    val next = current.clone() as Calendar
    when (period) {
        TendencyPeriod.DAILY -> next.add(Calendar.DAY_OF_MONTH, amount)
        TendencyPeriod.WEEKLY -> next.add(Calendar.WEEK_OF_YEAR, amount)
        TendencyPeriod.MONTHLY -> next.add(Calendar.MONTH, amount)
    }
    return next
}

private fun getTrendPointLabel(
    trendPeriod: TrendPeriod,
    date: Calendar
): String {
    return when (trendPeriod) {
        TrendPeriod.WEEKLY -> "${date.get(Calendar.MONTH) + 1}월 ${getWeekOfMonthMondayStart(date)}주"
        TrendPeriod.MONTHLY -> "${date.get(Calendar.MONTH) + 1}월"
    }
}

private fun getWeekOfMonthMondayStart(date: Calendar): Int {
    val firstDay = date.clone() as Calendar
    firstDay.set(Calendar.DAY_OF_MONTH, 1)
    firstDay.set(Calendar.HOUR_OF_DAY, 0)
    firstDay.set(Calendar.MINUTE, 0)
    firstDay.set(Calendar.SECOND, 0)
    firstDay.set(Calendar.MILLISECOND, 0)

    val firstMonday = firstDay.clone() as Calendar
    val dayOfWeek = firstMonday.get(Calendar.DAY_OF_WEEK)
    val diff = when (dayOfWeek) {
        Calendar.MONDAY -> 0
        Calendar.SUNDAY -> 1
        else -> 9 - dayOfWeek
    }
    firstMonday.add(Calendar.DAY_OF_MONTH, diff)

    if (date.before(firstMonday)) return 1

    val diffMillis = date.timeInMillis - firstMonday.timeInMillis
    val diffDays = (diffMillis / (1000 * 60 * 60 * 24)).toInt()
    return diffDays / 7 + 1
}

private fun getMondayToSundayForTendency(base: Calendar): Pair<Calendar, Calendar> {
    val monday = base.clone() as Calendar
    val dayOfWeek = monday.get(Calendar.DAY_OF_WEEK)
    val diffToMonday = when (dayOfWeek) {
        Calendar.SUNDAY -> -6
        else -> Calendar.MONDAY - dayOfWeek
    }
    monday.add(Calendar.DAY_OF_MONTH, diffToMonday)
    monday.set(Calendar.HOUR_OF_DAY, 0)
    monday.set(Calendar.MINUTE, 0)
    monday.set(Calendar.SECOND, 0)
    monday.set(Calendar.MILLISECOND, 0)

    val sunday = monday.clone() as Calendar
    sunday.add(Calendar.DAY_OF_MONTH, 6)
    sunday.set(Calendar.HOUR_OF_DAY, 23)
    sunday.set(Calendar.MINUTE, 59)
    sunday.set(Calendar.SECOND, 59)
    sunday.set(Calendar.MILLISECOND, 999)

    return monday to sunday
}

private fun parseCalendarForTendency(text: String): Calendar? {
    val regex = Regex("""(\d{4})[.-](\d{1,2})[.-](\d{1,2})""")
    val match = regex.find(text) ?: return null
    val year = match.groupValues[1].toIntOrNull() ?: return null
    val month = match.groupValues[2].toIntOrNull() ?: return null
    val day = match.groupValues[3].toIntOrNull() ?: return null

    return Calendar.getInstance().apply {
        set(Calendar.YEAR, year)
        set(Calendar.MONTH, month - 1)
        set(Calendar.DAY_OF_MONTH, day)
        set(Calendar.HOUR_OF_DAY, 0)
        set(Calendar.MINUTE, 0)
        set(Calendar.SECOND, 0)
        set(Calendar.MILLISECOND, 0)
    }
}

private fun todayCalendarForTendency(): Calendar {
    return Calendar.getInstance().apply {
        set(Calendar.HOUR_OF_DAY, 0)
        set(Calendar.MINUTE, 0)
        set(Calendar.SECOND, 0)
        set(Calendar.MILLISECOND, 0)
    }
}

private fun isSameDayForTendency(a: Calendar, b: Calendar): Boolean {
    return a.get(Calendar.YEAR) == b.get(Calendar.YEAR) &&
            a.get(Calendar.MONTH) == b.get(Calendar.MONTH) &&
            a.get(Calendar.DAY_OF_MONTH) == b.get(Calendar.DAY_OF_MONTH)
}

private fun categoryColorByName(name: String): Color {
    return when (name) {
        "식재료" -> Color(0xFF17A99B)
        "간편식" -> Color(0xFF168FD3)
        "간식" -> Color(0xFF4C63D9)
        "음료" -> Color(0xFF7A55D9)
        "주류" -> Color(0xFFD94FAE)
        "생활용품" -> Color(0xFFD2D7DF)
        "반려동물" -> Color(0xFF9AA3B2)
        "기타" -> Color(0xFFD2D7DF)
        else -> Color(0xFFD2D7DF)
    }
}

private fun formatDashboardPrice(value: Int): String {
    return String.format(Locale.KOREA, "%,d", value)
}

private fun formatShortPrice(value: Int): String {
    return when {
        value >= 10000 -> "${formatTendencyPercent(value / 10000.0)}만"
        value > 0 -> "${formatDashboardPrice(value)}원"
        else -> "0원"
    }
}

private fun roundUpAmount(value: Int): Int {
    if (value <= 0) return 1000
    return when {
        value <= 10000 -> ceil(value / 1000.0).toInt() * 1000
        value <= 100000 -> ceil(value / 10000.0).toInt() * 10000
        else -> ceil(value / 100000.0).toInt() * 100000
    }
}

private fun formatTendencyPercent(value: Double): String {
    return if (value % 1.0 == 0.0) {
        value.toInt().toString()
    } else {
        String.format(Locale.KOREA, "%.1f", value)
    }
}
