package com.example.receiptapp.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.*
import androidx.compose.ui.unit.sp
import com.example.receiptapp.R

val Pretendard = FontFamily(
    Font(R.font.pretendard_regular, FontWeight.Normal),
    Font(R.font.pretendard_medium, FontWeight.Medium),
    Font(R.font.pretendard_semibold, FontWeight.SemiBold),
    Font(R.font.pretendard_bold, FontWeight.Bold),
    Font(R.font.pretendard_black, FontWeight.Black),
    Font(R.font.pretendard_extrabold, FontWeight.ExtraBold)
)

val Typography = Typography(

    // 큰 제목
    titleLarge = TextStyle(
        fontFamily = Pretendard,
        fontWeight = FontWeight.Bold,
        fontSize = 22.sp
    ),

    // 일반 본문
    bodyLarge = TextStyle(
        fontFamily = Pretendard,
        fontWeight = FontWeight.Normal,
        fontSize = 16.sp
    ),

    // 버튼 텍스트
    labelLarge = TextStyle(
        fontFamily = Pretendard,
        fontWeight = FontWeight.SemiBold,
        fontSize = 14.sp
    )
)