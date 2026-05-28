package com.example.receiptapp.screen

import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.ReceiptLong
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
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
import coil.compose.AsyncImage
import java.util.Calendar

data class ReceiptListUi(
    val id: Int,
    val storeName: String,
    val analyzedAtText: String,
    val paymentTotal: Int,
    val imageUri: Uri? = null
)

private data class ReceiptDate(
    val year: Int,
    val month: Int,
    val day: Int
)

@Composable
fun ReceiptScreen(
    receipts: List<ReceiptListUi>,
    onReceiptClick: (ReceiptListUi) -> Unit
) {
    var currentYear by remember { mutableStateOf(initialYear(receipts)) }
    var currentMonth by remember { mutableStateOf(initialMonth(receipts)) }
    var selectedDate by remember { mutableStateOf<ReceiptDate?>(null) }

    val selectedReceipts = remember(receipts, selectedDate) {
        if (selectedDate == null) {
            emptyList()
        } else {
            receipts.filter { parseReceiptDate(it.analyzedAtText) == selectedDate }
        }
    }

    if (selectedDate == null) {
        ReceiptCalendarScreen(
            receipts = receipts,
            year = currentYear,
            month = currentMonth,
            onPrevMonth = {
                val cal = Calendar.getInstance()
                cal.set(currentYear, currentMonth - 1, 1)
                cal.add(Calendar.MONTH, -1)
                currentYear = cal.get(Calendar.YEAR)
                currentMonth = cal.get(Calendar.MONTH) + 1
            },
            onNextMonth = {
                val cal = Calendar.getInstance()
                cal.set(currentYear, currentMonth - 1, 1)
                cal.add(Calendar.MONTH, 1)
                currentYear = cal.get(Calendar.YEAR)
                currentMonth = cal.get(Calendar.MONTH) + 1
            },
            onDateClick = { date ->
                selectedDate = date
            }
        )
    } else {
        ReceiptDateListScreen(
            selectedDate = selectedDate!!,
            receipts = selectedReceipts,
            onBackClick = {
                selectedDate = null
            },
            onReceiptClick = onReceiptClick
        )
    }
}

@Composable
private fun ReceiptCalendarScreen(
    receipts: List<ReceiptListUi>,
    year: Int,
    month: Int,
    onPrevMonth: () -> Unit,
    onNextMonth: () -> Unit,
    onDateClick: (ReceiptDate) -> Unit
) {
    val receiptDates = receipts.mapNotNull { parseReceiptDate(it.analyzedAtText) }.toSet()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .padding(horizontal = 18.dp)
    ) {
        Spacer(modifier = Modifier.height(24.dp))

        Text(
            text = "내 영수증",
            fontSize = 26.sp,
            fontWeight = FontWeight.ExtraBold,
            color = Color(0xFF172033)
        )

        Spacer(modifier = Modifier.height(22.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "‹",
                fontSize = 30.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF172033),
                modifier = Modifier
                    .size(36.dp)
                    .clickable { onPrevMonth() },
                textAlign = TextAlign.Center
            )

            Text(
                text = "${year}년 ${month}월",
                modifier = Modifier.weight(1f),
                textAlign = TextAlign.Center,
                fontSize = 17.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF172033)
            )

            Text(
                text = "›",
                fontSize = 30.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF172033),
                modifier = Modifier
                    .size(36.dp)
                    .clickable { onNextMonth() },
                textAlign = TextAlign.Center
            )
        }

        Spacer(modifier = Modifier.height(18.dp))

        CalendarView(
            year = year,
            month = month,
            receiptDates = receiptDates,
            onDateClick = onDateClick
        )
    }
}

@Composable
private fun CalendarView(
    year: Int,
    month: Int,
    receiptDates: Set<ReceiptDate>,
    onDateClick: (ReceiptDate) -> Unit
) {
    val daysOfWeek = listOf("일", "월", "화", "수", "목", "금", "토")
    val calendarDays = remember(year, month) {
        buildCalendarDays(year, month)
    }

    Column {
        Row(modifier = Modifier.fillMaxWidth()) {
            daysOfWeek.forEach { day ->
                Text(
                    text = day,
                    modifier = Modifier.weight(1f),
                    textAlign = TextAlign.Center,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFF8A93A3)
                )
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        calendarDays.chunked(7).forEach { week ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(46.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                week.forEach { day ->
                    if (day == null) {
                        Box(modifier = Modifier.weight(1f))
                    } else {
                        val date = ReceiptDate(year, month, day)
                        val hasReceipt = receiptDates.contains(date)

                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .fillMaxHeight(),
                            contentAlignment = Alignment.Center
                        ) {
                            Column(
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.Center,
                                modifier = Modifier
                                    .size(38.dp)
                                    .clip(CircleShape)
                                    .background(
                                        if (hasReceipt) Color(0xFF4F46E5)
                                        else Color.Transparent
                                    )
                                    .clickable {
                                        onDateClick(date)
                                    }
                            ) {
                                Text(
                                    text = day.toString(),
                                    fontSize = 13.sp,
                                    fontWeight = if (hasReceipt) FontWeight.Bold else FontWeight.Medium,
                                    color = if (hasReceipt) Color.White else Color(0xFF172033)
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ReceiptDateListScreen(
    selectedDate: ReceiptDate,
    receipts: List<ReceiptListUi>,
    onBackClick: () -> Unit,
    onReceiptClick: (ReceiptListUi) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .padding(horizontal = 18.dp)
    ) {
        Spacer(modifier = Modifier.height(24.dp))

        Box(
            modifier = Modifier.fillMaxWidth(),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "‹",
                fontSize = 30.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF172033),
                modifier = Modifier
                    .align(Alignment.CenterStart)
                    .size(36.dp)
                    .clickable { onBackClick() },
                textAlign = TextAlign.Center
            )

            Text(
                text = "${selectedDate.year}.${two(selectedDate.month)}.${two(selectedDate.day)}",
                fontSize = 17.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF172033)
            )
        }

        Spacer(modifier = Modifier.height(20.dp))

        Text(
            text = "총 ${receipts.size}개의 영수증",
            fontSize = 13.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF4F46E5)
        )

        Spacer(modifier = Modifier.height(14.dp))

        if (receipts.isEmpty()) {
            EmptyReceiptView("해당 날짜에 등록된 영수증이 없습니다.")
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(bottom = 110.dp)
            ) {
                itemsIndexed(receipts) { index, receipt ->
                    ReceiptListCard(
                        receipt = receipt,
                        onClick = { onReceiptClick(receipt) }
                    )

                    if (index != receipts.lastIndex) {
                        Spacer(modifier = Modifier.height(10.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun ReceiptListCard(
    receipt: ReceiptListUi,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .border(
                width = 1.dp,
                color = Color(0xFFE5E7EB),
                shape = RoundedCornerShape(14.dp)
            )
            .background(Color.White)
            .clickable { onClick() }
            .padding(horizontal = 14.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        if (receipt.imageUri != null) {
            AsyncImage(
                model = receipt.imageUri,
                contentDescription = "영수증 이미지",
                modifier = Modifier
                    .width(42.dp)
                    .height(52.dp)
                    .clip(RoundedCornerShape(10.dp)),
                contentScale = ContentScale.Crop
            )
        } else {
            Box(
                modifier = Modifier
                    .size(42.dp)
                    .clip(CircleShape)
                    .background(Color(0xFFEFF6FF)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.ReceiptLong,
                    contentDescription = null,
                    tint = Color(0xFF4F46E5),
                    modifier = Modifier.size(22.dp)
                )
            }
        }

        Spacer(modifier = Modifier.width(12.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = receipt.storeName,
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF172033)
            )

            Spacer(modifier = Modifier.height(4.dp))

            Text(
                text = receipt.analyzedAtText,
                fontSize = 12.sp,
                color = Color(0xFF7B8494)
            )
        }

        Text(
            text = "${formatPrice(receipt.paymentTotal)}원",
            fontSize = 13.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF172033)
        )

        Spacer(modifier = Modifier.width(6.dp))

        Icon(
            imageVector = Icons.Default.ChevronRight,
            contentDescription = "상세 보기",
            tint = Color(0xFFC1C7D0),
            modifier = Modifier.size(22.dp)
        )
    }
}

@Composable
private fun EmptyReceiptView(
    message: String = "아직 저장된 영수증이 없습니다."
) {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = message,
            fontSize = 15.sp,
            color = Color(0xFF9AA3B2)
        )
    }
}

private fun buildCalendarDays(year: Int, month: Int): List<Int?> {
    val cal = Calendar.getInstance()
    cal.set(year, month - 1, 1)

    val firstDayOfWeek = cal.get(Calendar.DAY_OF_WEEK)
    val maxDay = cal.getActualMaximum(Calendar.DAY_OF_MONTH)

    val blanks = List(firstDayOfWeek - 1) { null }
    val days = (1..maxDay).map { it as Int? }

    val result = (blanks + days).toMutableList()

    while (result.size % 7 != 0) {
        result.add(null)
    }

    return result
}

private fun parseReceiptDate(text: String): ReceiptDate? {
    val regex = Regex("""(\d{4})[.-](\d{1,2})[.-](\d{1,2})""")
    val match = regex.find(text) ?: return null

    val year = match.groupValues[1].toIntOrNull() ?: return null
    val month = match.groupValues[2].toIntOrNull() ?: return null
    val day = match.groupValues[3].toIntOrNull() ?: return null

    return ReceiptDate(year, month, day)
}

private fun initialYear(receipts: List<ReceiptListUi>): Int {
    val firstDate = receipts.firstNotNullOfOrNull { parseReceiptDate(it.analyzedAtText) }
    return firstDate?.year ?: Calendar.getInstance().get(Calendar.YEAR)
}

private fun initialMonth(receipts: List<ReceiptListUi>): Int {
    val firstDate = receipts.firstNotNullOfOrNull { parseReceiptDate(it.analyzedAtText) }
    return firstDate?.month ?: Calendar.getInstance().get(Calendar.MONTH) + 1
}

private fun two(value: Int): String {
    return value.toString().padStart(2, '0')
}