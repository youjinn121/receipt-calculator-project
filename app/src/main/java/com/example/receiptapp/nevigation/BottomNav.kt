package com.example.receiptapp.navigation

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

data class BottomNavItem(
    val title: String,
    val icon: ImageVector
)

@Composable
fun CustomBottomNavigation(
    items: List<BottomNavItem>,
    selectedIndex: Int,
    onItemClick: (Int) -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()

            // ↓ 네비게이션 자체를 더 아래로
            .padding(
                start = 20.dp,
                end = 20.dp,
                bottom = 6.dp
            )

            // ↓ 전체 높이 아주 살짝 감소
            .height(70.dp),
        contentAlignment = Alignment.Center
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 8.dp),
            horizontalArrangement = Arrangement.SpaceEvenly,
            verticalAlignment = Alignment.CenterVertically
        ) {
            items.forEachIndexed { index, item ->
                NavButton(
                    item = item,
                    selected = selectedIndex == index,
                    onClick = { onItemClick(index) }
                )
            }
        }
    }
}

@Composable
fun NavButton(
    item: BottomNavItem,
    selected: Boolean,
    onClick: () -> Unit
) {
    val backgroundColor =
        if (selected) Color(0xFFE8F0FF) else Color.Transparent

    val iconColor =
        if (selected) Color(0xFF1769FF) else Color(0xFF777777)

    val textColor =
        if (selected) Color(0xFF1769FF) else Color(0xFF777777)

    Column(
        modifier = Modifier
            .width(100.dp)
            .height(54.dp)
            .clip(RoundedCornerShape(34.dp))
            .background(backgroundColor)
            .clickable { onClick() },

        horizontalAlignment = Alignment.CenterHorizontally,

        // ↓ 간격 거의 제거
        verticalArrangement = Arrangement.spacedBy((-2).dp)
    ) {

        Box(
            modifier = Modifier
                .size(32.dp)
                .clip(CircleShape),

            contentAlignment = Alignment.Center
        ) {

            Icon(
                imageVector = item.icon,
                contentDescription = item.title,
                tint = iconColor,

                // ↓ 아이콘 아주 살짝 축소
                modifier = Modifier.size(23.dp)
            )
        }

        // ↓ 아이콘과 글자 간격 아주 조금 감소
        Spacer(modifier = Modifier.height(0.5.dp))

        Text(
            text = item.title,
            fontSize = 12.2.sp,
            fontWeight =
                if (selected) FontWeight.Bold
                else FontWeight.Medium,

            color = textColor,
            maxLines = 1
        )
    }
}