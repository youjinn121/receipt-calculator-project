package com.example.receiptapp.screen

import android.net.Uri
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.rememberAsyncImagePainter

@Composable
fun PreviewScreen(
    imageUri: Uri?,
    onBackClick: () -> Unit,
    onRetakeClick: () -> Unit,
    onCompleteClick: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF8FAFD))
            .padding(horizontal = 4.dp)
    ) {
        Spacer(modifier = Modifier.height(12.dp))

        // 상단 바
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
                    tint = Color(0xFF172033)
                )
            }

            Text(
                text = "업로드",
                fontSize = 26.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFF172033),
                textAlign = TextAlign.Center
            )
        }

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = "영수증을 확인하고 완료할 수 있습니다",
            modifier = Modifier.fillMaxWidth(),
            fontSize = 14.sp,
            color = Color(0xFF7B8494),
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(24.dp))

        // 📸 이미지 미리보기
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(430.dp)
                .clip(RoundedCornerShape(20.dp))
                .background(Color.White)
                .border(
                    width = 1.dp,
                    color = Color(0xFFD7DEE9),
                    shape = RoundedCornerShape(20.dp)
                ),
            contentAlignment = Alignment.Center
        ) {
            if (imageUri != null) {
                Image(
                    painter = rememberAsyncImagePainter(imageUri),
                    contentDescription = "촬영된 영수증",
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Fit
                )
            } else {
                Text(
                    text = "촬영된 영수증 미리보기",
                    fontSize = 14.sp,
                    color = Color(0xFF9AA3B2)
                )
            }
        }

        Spacer(modifier = Modifier.weight(1f))

        // 🔥 버튼 영역
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 24.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {

            // 다시 찍기 버튼
            Button(
                onClick = onRetakeClick,
                modifier = Modifier
                    .weight(1f)
                    .height(56.dp)
                    .shadow(
                        elevation = 4.dp,
                        shape = RoundedCornerShape(12.dp)
                    ),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFFF1F3F7)
                )
            ) {
                Text(
                    text = "다시 찍기",
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF172033)
                )
            }

            // 완료하기 버튼
            Button(
                onClick = onCompleteClick,
                modifier = Modifier
                    .weight(1f)
                    .height(56.dp)
                    .shadow(
                        elevation = 6.dp,
                        shape = RoundedCornerShape(12.dp)
                    ),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFF1769FF)
                )
            ) {
                Text(
                    text = "완료하기",
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White
                )
            }
        }
    }
}