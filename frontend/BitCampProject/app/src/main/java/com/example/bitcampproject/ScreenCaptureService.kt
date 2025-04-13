package com.example.bitcampproject

import android.app.*
import android.content.Intent
import android.content.res.Resources
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.*
import android.util.Base64
import android.util.Log
import androidx.core.app.NotificationCompat
import java.io.ByteArrayOutputStream

class ScreenCaptureService : Service() {

    companion object {
        const val CHANNEL_ID = "ProjectionServiceChannel"
        var latestScreenshotBase64: String? = null
    }

    // Keep a local variable to track the last capture time
    private var lastCaptureTime: Long = 0L

    private var mediaProjection: MediaProjection? = null
    private lateinit var imageReader: ImageReader

    // Flag to ensure we only capture one screenshot
    private var hasCapturedScreenshot = false

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Screen Capture Running")
            .setContentText("Your screen is being accessed.")
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .build()

        startForeground(1, notification)
        Log.d("ScreenCaptureService", "Foreground service started")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val resultCode = intent?.getIntExtra("resultCode", Activity.RESULT_CANCELED)
        val resultData = intent?.getParcelableExtra<Intent>("data")

        if (resultCode != null && resultData != null) {
            val projectionManager = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            mediaProjection = projectionManager.getMediaProjection(resultCode, resultData)
            mediaProjection?.registerCallback(mediaProjectionCallback, Handler(Looper.getMainLooper()))
            setupVirtualDisplay()
        } else {
            Log.e("ScreenCaptureService", "MediaProjection setup failed: resultCode or data missing")
        }

        return START_STICKY
    }

    private val mediaProjectionCallback = object : MediaProjection.Callback() {
        override fun onStop() {
            super.onStop()
            Log.d("ScreenCaptureService", "MediaProjection stopped")
            imageReader.close()
            mediaProjection = null
        }
    }

    private fun setupVirtualDisplay() {
        val metrics = Resources.getSystem().displayMetrics
        imageReader = ImageReader.newInstance(
            metrics.widthPixels,
            metrics.heightPixels,
            PixelFormat.RGBA_8888,
            /* maxImages */ 2
        )

        mediaProjection?.createVirtualDisplay(
            "ScreenCapture",
            metrics.widthPixels,
            metrics.heightPixels,
            metrics.densityDpi,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            imageReader.surface,
            null,
            null
        )

        // Capture only the first available image
        imageReader.setOnImageAvailableListener({ reader ->
            val image = reader.acquireLatestImage() ?: return@setOnImageAvailableListener

            // Only capture once every 1000ms (1 second)
            val now = System.currentTimeMillis()
            if (now - lastCaptureTime >= 1000) {
                lastCaptureTime = now

                // ---- Perform your normal capture -> Base64 logic ----
                val planes = image.planes
                val buffer = planes[0].buffer
                val pixelStride = planes[0].pixelStride
                val rowStride = planes[0].rowStride
                val rowPadding = rowStride - pixelStride * image.width

                val bitmap = Bitmap.createBitmap(
                    image.width + rowPadding / pixelStride,
                    image.height,
                    Bitmap.Config.ARGB_8888
                )
                bitmap.copyPixelsFromBuffer(buffer)

                // Convert to Base64
                val stream = ByteArrayOutputStream()
                bitmap.compress(Bitmap.CompressFormat.JPEG, 70, stream)
                latestScreenshotBase64 = Base64.encodeToString(stream.toByteArray(), Base64.NO_WRAP)

                Log.d("ScreenCaptureService", "Screenshot captured: ${latestScreenshotBase64?.length} chars")
            }

            // Always close the image to free up resources
            image.close()

        }, Handler(Looper.getMainLooper()))

    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Screen Capture Notification",
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }
}
