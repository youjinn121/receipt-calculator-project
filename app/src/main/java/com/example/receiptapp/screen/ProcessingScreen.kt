package com.example.receiptapp.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Article
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.DataObject
import androidx.compose.material.icons.filled.DocumentScanner
import androidx.compose.material.icons.filled.Verified
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun ProcessingScreen() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF8FAFD))
            .padding(horizontal = 4.dp)
    ) {
        Spacer(modifier = Modifier.height(60.dp))

        Text(
            text = "영수증 처리 중",
            fontSize = 26.sp,
            fontWeight = FontWeight.ExtraBold,
            color = Color(0xFF172033)
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = "영수증을 처리하고 있어요. 잠시만 기다려주세요.",
            fontSize = 14.sp,
            color = Color(0xFF7B8494)
        )

        Spacer(modifier = Modifier.height(48.dp))

        ProcessingStep(
            title = "OCR (텍스트 추출)",
            icon = Icons.Default.DocumentScanner,
            state = StepState.Done
        )

        ProcessingStep(
            title = "데이터 구조화",
            icon = Icons.Default.DataObject,
            state = StepState.Done
        )

        ProcessingStep(
            title = "데이터 검증",
            icon = Icons.Default.Verified,
            state = StepState.Loading
        )

        ProcessingStep(
            title = "결과 생성",
            icon = Icons.Default.Article,
            state = StepState.Waiting
        )
    }
}

enum class StepState {
    Done, Loading, Waiting
}

@Composable
fun ProcessingStep(
    title: String,
    icon: ImageVector,
    state: StepState
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(86.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(52.dp)
                .background(
                    color = if (state == StepState.Waiting) Color(0xFFE9EEF6) else Color(0xFFEAF2FF),
                    shape = CircleShape
                ),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = title,
                tint = if (state == StepState.Waiting) Color(0xFF9AA3B2) else Color(0xFF1769FF),
                modifier = Modifier.size(26.dp)
            )
        }

        Spacer(modifier = Modifier.width(18.dp))

        Text(
            text = title,
            modifier = Modifier.weight(1f),
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            color = if (state == StepState.Waiting) Color(0xFF8A94A6) else Color(0xFF172033)
        )

        when (state) {
            StepState.Done -> {
                Box(
                    modifier = Modifier
                        .size(28.dp)
                        .background(Color(0xFF1769FF), CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Check,
                        contentDescription = "완료",
                        tint = Color.White,
                        modifier = Modifier.size(18.dp)
                    )
                }
            }

            StepState.Loading -> {
                CircularProgressIndicator(
                    modifier = Modifier.size(28.dp),
                    strokeWidth = 3.dp,
                    color = Color(0xFF1769FF)
                )
            }

            StepState.Waiting -> {
                Box(
                    modifier = Modifier
                        .size(22.dp)
                        .background(Color.Transparent, CircleShape)
                )
            }
        }
    }
}