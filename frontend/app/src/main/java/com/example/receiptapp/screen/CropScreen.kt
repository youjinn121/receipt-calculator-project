package com.example.receiptapp.screen

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import android.net.Uri
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathFillType
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.*
import coil.compose.rememberAsyncImagePainter
import java.io.File
import java.io.FileOutputStream
import kotlin.math.min
import kotlin.math.roundToInt

@Composable
fun CropScreen(
    imageUri: Uri?,
    onRetakeClick: () -> Unit,
    onCompleteClick: (Uri?) -> Unit
) {
    val context = LocalContext.current
    val density = LocalDensity.current

    var containerSize by remember { mutableStateOf(IntSize.Zero) }

    var cropLeft by remember { mutableStateOf(100f) }
    var cropTop by remember { mutableStateOf(100f) }
    var cropWidth by remember { mutableStateOf(500f) }
    var cropHeight by remember { mutableStateOf(700f) }

    val minCropWidth = 120f
    val minCropHeight = 180f

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .padding(10.dp)
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .clip(RoundedCornerShape(20.dp))
                .background(Color.White)
                .border(1.dp, Color(0xFFF1F3F6), RoundedCornerShape(20.dp))
                .onSizeChanged { size ->
                    containerSize = size

                    if (imageUri != null && size.width > 0 && size.height > 0) {
                        val bitmap = loadBitmapWithCorrectOrientation(context, imageUri)

                        if (bitmap != null) {
                            val scale = min(
                                size.width / bitmap.width.toFloat(),
                                size.height / bitmap.height.toFloat()
                            )

                            val displayedWidth = bitmap.width * scale
                            val displayedHeight = bitmap.height * scale

                            val left = (size.width - displayedWidth) / 2f
                            val top = (size.height - displayedHeight) / 2f

                            cropLeft = left + 20f
                            cropTop = top + 20f
                            cropWidth = displayedWidth - 40f
                            cropHeight = displayedHeight - 40f

                            cropLeft = cropLeft.coerceIn(0f, size.width - cropWidth)
                            cropTop = cropTop.coerceIn(0f, size.height - cropHeight)

                            bitmap.recycle()
                        }
                    }
                }
        ) {
            if (imageUri != null) {
                Image(
                    painter = rememberAsyncImagePainter(imageUri),
                    contentDescription = null,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Fit
                )
            }

            CropDarkOverlay(
                cropLeft = cropLeft,
                cropTop = cropTop,
                cropWidth = cropWidth,
                cropHeight = cropHeight
            )

            Box(
                modifier = Modifier
                    .offset {
                        IntOffset(
                            cropLeft.roundToInt(),
                            cropTop.roundToInt()
                        )
                    }
                    .width(with(density) { cropWidth.toDp() })
                    .height(with(density) { cropHeight.toDp() })
                    .pointerInput(containerSize, cropWidth, cropHeight) {
                        detectDragGestures { change, drag ->
                            change.consume()

                            if (containerSize.width <= 0 || containerSize.height <= 0) {
                                return@detectDragGestures
                            }

                            cropLeft = (cropLeft + drag.x)
                                .coerceIn(0f, containerSize.width - cropWidth)

                            cropTop = (cropTop + drag.y)
                                .coerceIn(0f, containerSize.height - cropHeight)
                        }
                    }
            ) {
                CropGuideCanvas()

                InvisibleResizeHandle(
                    modifier = Modifier.align(Alignment.TopStart)
                ) { dx, dy ->
                    val right = cropLeft + cropWidth
                    val bottom = cropTop + cropHeight

                    val newLeft = (cropLeft + dx)
                        .coerceIn(0f, right - minCropWidth)

                    val newTop = (cropTop + dy)
                        .coerceIn(0f, bottom - minCropHeight)

                    cropWidth = right - newLeft
                    cropHeight = bottom - newTop
                    cropLeft = newLeft
                    cropTop = newTop
                }

                InvisibleResizeHandle(
                    modifier = Modifier.align(Alignment.TopEnd)
                ) { dx, dy ->
                    val bottom = cropTop + cropHeight

                    val newRight = (cropLeft + cropWidth + dx)
                        .coerceIn(cropLeft + minCropWidth, containerSize.width.toFloat())

                    val newTop = (cropTop + dy)
                        .coerceIn(0f, bottom - minCropHeight)

                    cropWidth = newRight - cropLeft
                    cropHeight = bottom - newTop
                    cropTop = newTop
                }

                InvisibleResizeHandle(
                    modifier = Modifier.align(Alignment.BottomStart)
                ) { dx, dy ->
                    val right = cropLeft + cropWidth

                    val newLeft = (cropLeft + dx)
                        .coerceIn(0f, right - minCropWidth)

                    val newBottom = (cropTop + cropHeight + dy)
                        .coerceIn(cropTop + minCropHeight, containerSize.height.toFloat())

                    cropWidth = right - newLeft
                    cropHeight = newBottom - cropTop
                    cropLeft = newLeft
                }

                InvisibleResizeHandle(
                    modifier = Modifier.align(Alignment.BottomEnd)
                ) { dx, dy ->
                    val newRight = (cropLeft + cropWidth + dx)
                        .coerceIn(cropLeft + minCropWidth, containerSize.width.toFloat())

                    val newBottom = (cropTop + cropHeight + dy)
                        .coerceIn(cropTop + minCropHeight, containerSize.height.toFloat())

                    cropWidth = newRight - cropLeft
                    cropHeight = newBottom - cropTop
                }
            }
        }

        Spacer(modifier = Modifier.height(20.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Button(
                onClick = onRetakeClick,
                modifier = Modifier
                    .weight(1f)
                    .height(58.dp),
                shape = RoundedCornerShape(30.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFFE9EEF5),
                    contentColor = Color(0xFF4B5563)
                ),
                elevation = ButtonDefaults.buttonElevation(
                    defaultElevation = 2.dp
                )
            ) {
                Text(
                    text = "다시 찍기",
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Medium
                )
            }

            Button(
                onClick = {
                    if (imageUri == null) {
                        onCompleteClick(null)
                        return@Button
                    }

                    val cropped = cropImageByRect(
                        context = context,
                        imageUri = imageUri,
                        containerWidth = containerSize.width,
                        containerHeight = containerSize.height,
                        cropRect = Rect(
                            cropLeft,
                            cropTop,
                            cropLeft + cropWidth,
                            cropTop + cropHeight
                        )
                    )

                    onCompleteClick(cropped)
                },
                modifier = Modifier
                    .weight(1f)
                    .height(58.dp),
                shape = RoundedCornerShape(30.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFF1769FF),
                    contentColor = Color.White
                ),
                elevation = ButtonDefaults.buttonElevation(
                    defaultElevation = 4.dp
                )
            ) {
                Text(
                    text = "완료하기",
                    fontSize = 15.sp,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }
    }
}

@Composable
fun CropDarkOverlay(
    cropLeft: Float,
    cropTop: Float,
    cropWidth: Float,
    cropHeight: Float
) {
    Canvas(modifier = Modifier.fillMaxSize()) {
        val cropRect = Rect(
            left = cropLeft,
            top = cropTop,
            right = cropLeft + cropWidth,
            bottom = cropTop + cropHeight
        )

        val path = Path().apply {
            fillType = PathFillType.EvenOdd

            addRect(
                Rect(
                    left = 0f,
                    top = 0f,
                    right = size.width,
                    bottom = size.height
                )
            )

            addRoundRect(
                androidx.compose.ui.geometry.RoundRect(
                    rect = cropRect,
                    cornerRadius = androidx.compose.ui.geometry.CornerRadius(
                        x = 18.dp.toPx(),
                        y = 18.dp.toPx()
                    )
                )
            )
        }

        drawPath(
            path = path,
            color = Color.Black.copy(alpha = 0.35f)
        )
    }
}

@Composable
fun CropGuideCanvas() {
    Canvas(modifier = Modifier.fillMaxSize()) {
        val blue = Color(0xFF1769FF)
        val strokeWidth = 4.dp.toPx()
        val cornerLength = 34.dp.toPx()
        val radius = 16.dp.toPx()

        drawRoundRect(
            color = blue.copy(alpha = 0.65f),
            style = Stroke(width = 1.5.dp.toPx()),
            cornerRadius = androidx.compose.ui.geometry.CornerRadius(radius, radius)
        )

        drawLine(blue, Offset(0f, 0f), Offset(cornerLength, 0f), strokeWidth, StrokeCap.Round)
        drawLine(blue, Offset(0f, 0f), Offset(0f, cornerLength), strokeWidth, StrokeCap.Round)

        drawLine(blue, Offset(size.width, 0f), Offset(size.width - cornerLength, 0f), strokeWidth, StrokeCap.Round)
        drawLine(blue, Offset(size.width, 0f), Offset(size.width, cornerLength), strokeWidth, StrokeCap.Round)

        drawLine(blue, Offset(0f, size.height), Offset(cornerLength, size.height), strokeWidth, StrokeCap.Round)
        drawLine(blue, Offset(0f, size.height), Offset(0f, size.height - cornerLength), strokeWidth, StrokeCap.Round)

        drawLine(blue, Offset(size.width, size.height), Offset(size.width - cornerLength, size.height), strokeWidth, StrokeCap.Round)
        drawLine(blue, Offset(size.width, size.height), Offset(size.width, size.height - cornerLength), strokeWidth, StrokeCap.Round)
    }
}

@Composable
fun InvisibleResizeHandle(
    modifier: Modifier = Modifier,
    onDrag: (Float, Float) -> Unit
) {
    Box(
        modifier = modifier
            .size(56.dp)
            .pointerInput(Unit) {
                detectDragGestures { change, drag ->
                    change.consume()
                    onDrag(drag.x, drag.y)
                }
            }
    )
}

fun cropImageByRect(
    context: Context,
    imageUri: Uri,
    containerWidth: Int,
    containerHeight: Int,
    cropRect: Rect
): Uri? {
    if (containerWidth <= 0 || containerHeight <= 0) return imageUri

    val bitmap = loadBitmapWithCorrectOrientation(context, imageUri)
        ?: return imageUri

    val bitmapWidth = bitmap.width.toFloat()
    val bitmapHeight = bitmap.height.toFloat()

    val scale = min(
        containerWidth / bitmapWidth,
        containerHeight / bitmapHeight
    )

    val displayedWidth = bitmapWidth * scale
    val displayedHeight = bitmapHeight * scale

    val imageLeftInContainer = (containerWidth - displayedWidth) / 2f
    val imageTopInContainer = (containerHeight - displayedHeight) / 2f

    val cropLeftOnBitmap =
        ((cropRect.left - imageLeftInContainer) / scale).roundToInt()
            .coerceIn(0, bitmap.width - 1)

    val cropTopOnBitmap =
        ((cropRect.top - imageTopInContainer) / scale).roundToInt()
            .coerceIn(0, bitmap.height - 1)

    val cropRightOnBitmap =
        ((cropRect.right - imageLeftInContainer) / scale).roundToInt()
            .coerceIn(cropLeftOnBitmap + 1, bitmap.width)

    val cropBottomOnBitmap =
        ((cropRect.bottom - imageTopInContainer) / scale).roundToInt()
            .coerceIn(cropTopOnBitmap + 1, bitmap.height)

    val croppedBitmap = Bitmap.createBitmap(
        bitmap,
        cropLeftOnBitmap,
        cropTopOnBitmap,
        cropRightOnBitmap - cropLeftOnBitmap,
        cropBottomOnBitmap - cropTopOnBitmap
    )

    val outputDir = File(context.cacheDir, "cropped_receipts")
    if (!outputDir.exists()) outputDir.mkdirs()

    val outputFile = File(
        outputDir,
        "CROPPED_RECEIPT_${System.currentTimeMillis()}.jpg"
    )

    FileOutputStream(outputFile).use { out ->
        croppedBitmap.compress(Bitmap.CompressFormat.JPEG, 95, out)
    }

    bitmap.recycle()
    croppedBitmap.recycle()

    return Uri.fromFile(outputFile)
}

fun loadBitmapWithCorrectOrientation(
    context: Context,
    imageUri: Uri
): Bitmap? {
    val bitmapInputStream = context.contentResolver.openInputStream(imageUri)
        ?: return null

    val originalBitmap = BitmapFactory.decodeStream(bitmapInputStream)
    bitmapInputStream.close()

    if (originalBitmap == null) return null

    val exifInputStream = context.contentResolver.openInputStream(imageUri)
        ?: return originalBitmap

    val exif = ExifInterface(exifInputStream)
    val orientation = exif.getAttributeInt(
        ExifInterface.TAG_ORIENTATION,
        ExifInterface.ORIENTATION_NORMAL
    )
    exifInputStream.close()

    val rotationDegrees = when (orientation) {
        ExifInterface.ORIENTATION_ROTATE_90 -> 90f
        ExifInterface.ORIENTATION_ROTATE_180 -> 180f
        ExifInterface.ORIENTATION_ROTATE_270 -> 270f
        else -> 0f
    }

    if (rotationDegrees == 0f) {
        return originalBitmap
    }

    val matrix = Matrix().apply {
        postRotate(rotationDegrees)
    }

    val rotatedBitmap = Bitmap.createBitmap(
        originalBitmap,
        0,
        0,
        originalBitmap.width,
        originalBitmap.height,
        matrix,
        true
    )

    originalBitmap.recycle()

    return rotatedBitmap
}