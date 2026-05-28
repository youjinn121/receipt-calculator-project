package com.example.receiptapp.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun StoreSelectScreen(
    selectedStore: String,
    onStoreSelected: (String) -> Unit,
    onBackClick: () -> Unit,
    onStartClick: () -> Unit
) {
    val stores = listOf("emart", "costco", "hanaro")
    var expanded by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFFF8FAFD))
            .padding(horizontal = 4.dp)
    ) {
        Spacer(modifier = Modifier.height(12.dp))

        IconButton(onClick = onBackClick) {
            Icon(
                imageVector = Icons.Default.ArrowBack,
                contentDescription = "뒤로가기",
                tint = Color(0xFF172033)
            )
        }

        Spacer(modifier = Modifier.height(18.dp))

        Text(
            text = "스토어 선택",
            fontSize = 26.sp,
            fontWeight = FontWeight.ExtraBold,
            color = Color(0xFF172033)
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = "영수증을 발급한 매장을 선택해주세요.",
            fontSize = 14.sp,
            color = Color(0xFF7B8494)
        )

        Spacer(modifier = Modifier.height(34.dp))

        Spacer(modifier = Modifier.height(8.dp))

        Box {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp)
                    .background(Color.White, RoundedCornerShape(14.dp))
                    .border(
                        width = 1.dp,
                        color = Color(0xFFD7DEE9),
                        shape = RoundedCornerShape(14.dp)
                    )
                    .clickable { expanded = true }
                    .padding(horizontal = 16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = if (selectedStore.isBlank()) "선택해주세요" else selectedStore,
                    modifier = Modifier.weight(1f),
                    fontSize = 15.sp,
                    color = if (selectedStore.isBlank()) Color(0xFF9AA3B2) else Color(0xFF172033)
                )

                Icon(
                    imageVector = Icons.Default.KeyboardArrowDown,
                    contentDescription = "스토어 선택",
                    tint = Color(0xFF172033)
                )
            }

            DropdownMenu(
                expanded = expanded,
                onDismissRequest = { expanded = false }
            ) {
                stores.forEach { store ->
                    DropdownMenuItem(
                        text = { Text(store) },
                        onClick = {
                            onStoreSelected(store)
                            expanded = false
                        }
                    )
                }
            }
        }

        Spacer(modifier = Modifier.weight(1f))

        Button(
            onClick = onStartClick,
            enabled = selectedStore.isNotBlank(),
            modifier = Modifier
                .fillMaxWidth()
                .height(58.dp),
            shape = RoundedCornerShape(10.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = Color(0xFF1769FF),
                disabledContainerColor = Color(0xFFBFD4FF)
            )
        ) {
            Text(
                text = "영수증 정보 추출하기",
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White
            )
        }

        Spacer(modifier = Modifier.height(24.dp))
    }
}