package com.example.bitcampproject

import android.os.Bundle
import android.widget.EditText
import android.widget.ImageButton
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class Screen1Activity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.screen1) // your layout file

        val etPrompt = findViewById<EditText>(R.id.etPrompt)
        val btnSend = findViewById<ImageButton>(R.id.btnCancel)       // ✅ tick button
        val btnClear = findViewById<ImageButton>(R.id.btnReset)       // ❌ clear button
        val btnMic = findViewById<ImageButton>(R.id.btnMic)           // 🎤 mic button

        // ✅ Send input
        btnSend.setOnClickListener {
            val userText = etPrompt.text.toString().trim()
            if (userText.isNotEmpty()) {
                Toast.makeText(this, "Sending: $userText", Toast.LENGTH_SHORT).show()
                // send this to your WebSocket or backend
            } else {
                Toast.makeText(this, "Please type something!", Toast.LENGTH_SHORT).show()
            }
        }

        // ❌ Clear input
        btnClear.setOnClickListener {
            etPrompt.text.clear()
        }

        // 🎤 Mic click (you can hook speech recognition here)
        btnMic.setOnClickListener {
            Toast.makeText(this, "Mic clicked", Toast.LENGTH_SHORT).show()
            // startVoiceRecognition() - optional to implement
        }
    }
}
