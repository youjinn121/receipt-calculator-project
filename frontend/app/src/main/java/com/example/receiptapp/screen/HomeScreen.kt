package com.example.receiptapp.screen

import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

@Composable
fun HomeScreen() {
    Text(
        text = "홈 화면",
        fontSize = 24.sp,
        fontWeight = FontWeight.Bold
    )
}