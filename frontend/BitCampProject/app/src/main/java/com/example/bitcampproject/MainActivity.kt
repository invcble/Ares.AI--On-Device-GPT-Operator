package com.example.bitcampproject

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.WebSocket
import java.util.*

class MainActivity : AppCompatActivity() {

    companion object {
        const val SCREEN_CAPTURE_REQUEST_CODE = 1001
        const val RECORD_AUDIO_PERMISSION_CODE = 1
    }

    private lateinit var okHttpClient: OkHttpClient
    private var webSocket: WebSocket? = null
    private var isScreenSharing = false
    private var screenCaptureIntent: Intent? = null
    private var screenCaptureResultCode: Int = Activity.RESULT_CANCELED

    private lateinit var etPrompt: EditText
    private lateinit var btnMic: ImageButton
    private var speechRecognizer: SpeechRecognizer? = null
    private var isListening = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        etPrompt = findViewById(R.id.etPrompt)
        btnMic = findViewById(R.id.btnMic)

        // Request microphone permission if not granted
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(android.Manifest.permission.RECORD_AUDIO),
                RECORD_AUDIO_PERMISSION_CODE
            )
        }

        // Initialize speech recognizer
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            Toast.makeText(this, "Speech recognition not available", Toast.LENGTH_SHORT).show()
            return
        }

        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)

        val speechIntent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 3000L)
        }

        speechRecognizer?.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {}
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(rmsdB: Float) {}
            override fun onBufferReceived(buffer: ByteArray?) {}
            override fun onEndOfSpeech() {}

            override fun onError(error: Int) {
                isListening = false
                Toast.makeText(this@MainActivity, "Speech Error: $error", Toast.LENGTH_SHORT).show()
            }

            override fun onResults(results: Bundle?) {
                isListening = false
                val data = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                etPrompt.setText(data?.get(0))
            }

            override fun onPartialResults(partialResults: Bundle?) {}
            override fun onEvent(eventType: Int, params: Bundle?) {}
        })

        btnMic.setOnClickListener {
            if (!isListening) {
                speechRecognizer?.startListening(speechIntent)
                isListening = true
                Toast.makeText(this, "Listening...", Toast.LENGTH_SHORT).show()
            } else {
                speechRecognizer?.stopListening()
                isListening = false
                Toast.makeText(this, "Stopped Listening", Toast.LENGTH_SHORT).show()
            }
        }

        // Initialize WebSocket client
        okHttpClient = OkHttpClient()

        val btnWebSocket = findViewById<ImageButton>(R.id.btnStartWebSocket)
        val btnToggleScreen = findViewById<ImageView>(R.id.btnToggleScreenShare)
        val btnClear = findViewById<ImageButton>(R.id.btnReset)

        btnWebSocket.setOnClickListener {
            openWebSocket()
        }
        btnClear.setOnClickListener {
            etPrompt.text.clear()
        }

//        btnToggleScreen = findViewById(R.id.btnToggleScreenShare)

        btnToggleScreen.setOnClickListener {
            if (!isScreenSharing) {
                requestScreenCapturePermission()
            } else {
                stopScreenCaptureService()
                isScreenSharing = false
                btnToggleScreen.setImageResource(R.drawable.ares_logo_1)
            }
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == RECORD_AUDIO_PERMISSION_CODE &&
            (grantResults.isEmpty() || grantResults[0] != PackageManager.PERMISSION_GRANTED)
        ) {
            Toast.makeText(this, "Microphone permission denied!", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onDestroy() {
        speechRecognizer?.destroy()
        super.onDestroy()
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
//            findViewById<Button>(R.id.btnToggleScreenShare).text = "Stop Screen Share"
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
        val userPrompt = etPrompt.text.toString().trim()

        val request = Request.Builder()
            .url("wss://5b07-65-113-61-98.ngrok-free.app") // Replace with your WebSocket URL
            .build()

        val listener = MyWebSocketListener(this, userPrompt)
        webSocket = okHttpClient.newWebSocket(request, listener)

        Toast.makeText(this, "WebSocket started", Toast.LENGTH_SHORT).show()
        Log.d("MainActivity", "WebSocket connection initiated.")
    }
}
