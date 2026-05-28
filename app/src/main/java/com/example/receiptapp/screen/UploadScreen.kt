package com.example.receiptapp.screen

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.ReceiptLong
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun UploadScreen(
    onCameraClick: () -> Unit,
    onGalleryClick: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF8FAFD))
            .padding(horizontal = 4.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Spacer(modifier = Modifier.height(24.dp))

        Text(
            text = "나의 영수증 분석",
            modifier = Modifier.fillMaxWidth(),
            fontSize = 25.sp,
            fontWeight = FontWeight.Black,
            letterSpacing = (-1.6).sp,
            color = Color(0xFF111827),
            textAlign = TextAlign.Start
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = "영수증을 촬영해 장바구니를 분석하세요",
            modifier = Modifier.fillMaxWidth(),
            fontSize = 14.sp,
            fontWeight = FontWeight.Medium,
            color = Color(0xFF7B8494),
            textAlign = TextAlign.Start
        )

        Spacer(modifier = Modifier.height(38.dp))

        UploadScanCard(
            onCameraClick = onCameraClick,
            onGalleryClick = onGalleryClick
        )
    }
}

@Composable
fun UploadScanCard(
    onCameraClick: () -> Unit,
    onGalleryClick: () -> Unit
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(330.dp)
                .background(Color.White, RoundedCornerShape(28.dp))
                .border(
                    width = 1.dp,
                    color = Color(0xFFE5EAF2),
                    shape = RoundedCornerShape(28.dp)
                ),
            contentAlignment = Alignment.Center
        ) {
            CornerBrackets()
            ReceiptPreview()
        }

        Spacer(modifier = Modifier.height(24.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {

            UploadActionButton(
                modifier = Modifier.weight(1f),
                title = "촬영하기",
                icon = Icons.Default.CameraAlt,
                onClick = onCameraClick
            )

            UploadActionButton(
                modifier = Modifier.weight(1f),
                title = "사진 선택",
                icon = Icons.Default.ReceiptLong,
                onClick = onGalleryClick
            )
        }
    }
}

@Composable
fun ReceiptPreview() {
    Surface(
        modifier = Modifier.size(width = 104.dp, height = 144.dp),
        shape = RoundedCornerShape(14.dp),
        color = Color.White,
        shadowElevation = 4.dp
    ) {
        Column(
            modifier = Modifier.padding(
                start = 14.dp,
                end = 14.dp,
                top = 18.dp,
                bottom = 14.dp
            ),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(
                imageVector = Icons.Default.ReceiptLong,
                contentDescription = "영수증",
                tint = Color(0xFFDDE3EC),
                modifier = Modifier.size(20.dp)
            )

            Spacer(modifier = Modifier.height(12.dp))

            ReceiptLine(width = 62)
            ReceiptLine(width = 46)
            ReceiptLine(width = 58)

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "₩ 25,000",
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF8A93A3),
                maxLines = 1
            )
        }
    }
}

@Composable
fun CornerBrackets() {
    Canvas(
        modifier = Modifier
            .fillMaxSize()
            .padding(48.dp)
    ) {
        val color = Color(0xFF1769FF)
        val strokeWidth = 2.5.dp.toPx()
        val length = 22.dp.toPx()

        drawLine(color, Offset(0f, 0f), Offset(length, 0f), strokeWidth, cap = StrokeCap.Round)
        drawLine(color, Offset(0f, 0f), Offset(0f, length), strokeWidth, cap = StrokeCap.Round)

        drawLine(color, Offset(size.width, 0f), Offset(size.width - length, 0f), strokeWidth, cap = StrokeCap.Round)
        drawLine(color, Offset(size.width, 0f), Offset(size.width, length), strokeWidth, cap = StrokeCap.Round)

        drawLine(color, Offset(0f, size.height), Offset(length, size.height), strokeWidth, cap = StrokeCap.Round)
        drawLine(color, Offset(0f, size.height), Offset(0f, size.height - length), strokeWidth, cap = StrokeCap.Round)

        drawLine(color, Offset(size.width, size.height), Offset(size.width - length, size.height), strokeWidth, cap = StrokeCap.Round)
        drawLine(color, Offset(size.width, size.height), Offset(size.width, size.height - length), strokeWidth, cap = StrokeCap.Round)
    }
}

@Composable
fun ReceiptLine(width: Int) {
    Box(
        modifier = Modifier
            .width(width.dp)
            .height(4.dp)
            .background(Color(0xFFF8FAFD), RoundedCornerShape(10.dp))
    )

    Spacer(modifier = Modifier.height(7.dp))
}

@Composable
fun UploadActionButton(
    modifier: Modifier = Modifier,
    title: String,
    icon: ImageVector,
    onClick: () -> Unit
) {
    Button(
        onClick = onClick,
        modifier = modifier.height(54.dp),
        shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = Color(0xFF1769FF)
        ),
        elevation = ButtonDefaults.buttonElevation(
            defaultElevation = 2.dp,
            pressedElevation = 0.dp
        )
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = icon,
                contentDescription = title,
                tint = Color.White,
                modifier = Modifier.size(20.dp)
            )

            Spacer(modifier = Modifier.width(8.dp))

            Text(
                text = title,
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White
            )
        }
    }
}