package com.example.receiptapp.screen

import android.content.Context
import android.net.Uri
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.material3.FloatingActionButton
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.geometry.Offset
import androidx.compose.foundation.Canvas
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import java.io.File
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.concurrent.Executor
import android.Manifest
import android.content.pm.PackageManager
import android.util.Log
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts

@Composable
fun CameraScreen(
    onCloseClick: () -> Unit,
    onPhotoCaptured: (Uri) -> Unit
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current

    var imageCapture by remember { mutableStateOf<ImageCapture?>(null) }

    var hasCameraPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.CAMERA
            ) == PackageManager.PERMISSION_GRANTED
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { granted ->
        hasCameraPermission = granted
    }

    LaunchedEffect(Unit) {
        if (!hasCameraPermission) {
            permissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    if (!hasCameraPermission) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Black),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "카메라 권한이 필요합니다.",
                color = Color.White
            )
        }
        return
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { ctx ->
                val previewView = PreviewView(ctx).apply {
                    scaleType = PreviewView.ScaleType.FILL_CENTER
                }

                val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)

                cameraProviderFuture.addListener({
                    val cameraProvider = cameraProviderFuture.get()

                    val preview = Preview.Builder()
                        .build()
                        .also {
                            it.setSurfaceProvider(previewView.surfaceProvider)
                        }

                    val capture = ImageCapture.Builder()
                        .setCaptureMode(ImageCapture.CAPTURE_MODE_MAXIMIZE_QUALITY)
                        .setJpegQuality(95)
                        .build()

                    imageCapture = capture

                    val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

                    try {
                        cameraProvider.unbindAll()
                        cameraProvider.bindToLifecycle(
                            lifecycleOwner,
                            cameraSelector,
                            preview,
                            capture
                        )
                    } catch (e: Exception) {
                        e.printStackTrace()
                    }
                }, ContextCompat.getMainExecutor(ctx))

                previewView
            }
        )

        IconButton(
            onClick = onCloseClick,
            modifier = Modifier
                .padding(top = 4.dp, start = 4.dp)
                .size(52.dp)
                .align(Alignment.TopStart)
        ) {
            Icon(
                imageVector = Icons.Default.Close,
                contentDescription = "닫기",
                tint = Color.White,
                modifier = Modifier.size(34.dp)
            )
        }

        FloatingActionButton(
            onClick = {
                val capture = imageCapture

                if (capture == null) {
                    Toast.makeText(context, "카메라 준비 중입니다. 잠시 후 다시 눌러주세요.", Toast.LENGTH_SHORT).show()
                    Log.d("CameraScreen", "imageCapture is null")
                    return@FloatingActionButton
                }

                takePhoto(
                    context = context,
                    imageCapture = capture,
                    executor = ContextCompat.getMainExecutor(context),
                    onPhotoCaptured = { uri ->
                        Log.d("CameraScreen", "사진 저장 성공: $uri")
                        onPhotoCaptured(uri)
                    }
                )
            },
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 22.dp)
                .size(74.dp),
            shape = CircleShape,
            containerColor = Color.White,
            contentColor = Color(0xFF1769FF)
        ) {
            Icon(
                imageVector = Icons.Default.CameraAlt,
                contentDescription = "사진 촬영",
                modifier = Modifier.size(32.dp)
            )
        }
    }
}

@Composable
fun CameraOverlay() {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth(0.78f)
                .height(430.dp)
                .border(
                    width = 2.dp,
                    color = Color(0xAAFFFFFF),
                    shape = RoundedCornerShape(20.dp)
                )
        ) {
            CameraCornerBrackets()
        }
    }
}

@Composable
fun CameraCornerBrackets() {
    Canvas(
        modifier = Modifier
            .fillMaxSize()
            .padding(22.dp)
    ) {
        val color = Color(0xFF1769FF)
        val strokeWidth = 4.dp.toPx()
        val length = 36.dp.toPx()

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

fun takePhoto(
    context: Context,
    imageCapture: ImageCapture,
    executor: Executor,
    onPhotoCaptured: (Uri) -> Unit
) {
    val photoFile = createImageFile(context)

    val outputOptions = ImageCapture.OutputFileOptions.Builder(photoFile).build()

    imageCapture.takePicture(
        outputOptions,
        executor,
        object : ImageCapture.OnImageSavedCallback {
            override fun onImageSaved(outputFileResults: ImageCapture.OutputFileResults) {
                onPhotoCaptured(Uri.fromFile(photoFile))
            }

            override fun onError(exception: ImageCaptureException) {
                exception.printStackTrace()
            }
        }
    )
}

fun createImageFile(context: Context): File {
    val timeStamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.KOREA).format(System.currentTimeMillis())
    val storageDir = File(context.cacheDir, "receipt_images")

    if (!storageDir.exists()) {
        storageDir.mkdirs()
    }

    return File(storageDir, "RECEIPT_$timeStamp.jpg")
}