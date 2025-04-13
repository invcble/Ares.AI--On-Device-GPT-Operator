package com.example.bitcampproject

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.WebSocket

class MainActivity : AppCompatActivity() {

    companion object {
        const val SCREEN_CAPTURE_REQUEST_CODE = 1001
    }

    private lateinit var okHttpClient: OkHttpClient
    private var webSocket: WebSocket? = null
    private var isScreenSharing = false
    private var screenCaptureIntent: Intent? = null
    private var screenCaptureResultCode: Int = Activity.RESULT_CANCELED

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        okHttpClient = OkHttpClient()

        val btnWebSocket = findViewById<Button>(R.id.btnStartWebSocket)
        val btnToggleScreen = findViewById<Button>(R.id.btnToggleScreenShare)

        btnWebSocket.setOnClickListener {
            openWebSocket()
        }

        btnToggleScreen.setOnClickListener {
            if (!isScreenSharing) {
                requestScreenCapturePermission()
            } else {
                stopScreenCaptureService()
                btnToggleScreen.text = "Start Screen Share"
            }
        }
    }

    private fun requestScreenCapturePermission() {
        val mpm = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        startActivityForResult(mpm.createScreenCaptureIntent(), SCREEN_CAPTURE_REQUEST_CODE)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        if (requestCode == SCREEN_CAPTURE_REQUEST_CODE && resultCode == Activity.RESULT_OK && data != null) {
            screenCaptureResultCode = resultCode
            screenCaptureIntent = data
            startScreenCaptureService()
            findViewById<Button>(R.id.btnToggleScreenShare).text = "Stop Screen Share"
        } else {
            Toast.makeText(this, "Screen capture permission denied!", Toast.LENGTH_SHORT).show()
        }
    }

    private fun startScreenCaptureService() {
        val intent = Intent(this, ScreenCaptureService::class.java).apply {
            putExtra("resultCode", screenCaptureResultCode)
            putExtra("data", screenCaptureIntent)
        }
        isScreenSharing = true
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun stopScreenCaptureService() {
        isScreenSharing = false
        stopService(Intent(this, ScreenCaptureService::class.java))
    }

    private fun openWebSocket() {
        val userPrompt = findViewById<EditText>(R.id.etPrompt).text.toString().trim()

        val request = Request.Builder()
            .url("wss://5b07-65-113-61-98.ngrok-free.app") // Replace with your WebSocket endpoint
            .build()

        val listener = MyWebSocketListener(this, userPrompt)
        webSocket = okHttpClient.newWebSocket(request, listener)

        Toast.makeText(this, "WebSocket started", Toast.LENGTH_SHORT).show()
        Log.d("MainActivity", "WebSocket connection initiated.")
    }
}
