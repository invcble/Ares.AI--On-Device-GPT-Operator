package com.example.bitcampproject

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.Toast
import android.speech.tts.TextToSpeech
import java.util.*

class ActionAccessibilityService : AccessibilityService() {

    companion object {
        // Holds a reference to this service if it's running
        var instance: ActionAccessibilityService? = null
    }

    private var tts: TextToSpeech? = null


    override fun onCreate() {
        super.onCreate()
        instance = this
    }

    override fun onDestroy() {
        super.onDestroy()
        instance = null
        tts?.stop()
        tts?.shutdown()
    }

    fun speak(text: String) {
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "ttsMessage")
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        Toast.makeText(this, "Accessibility Service Connected", Toast.LENGTH_SHORT).show()
        Log.d("ActionAccessibilityService", "onServiceConnected()")

        tts = TextToSpeech(this) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.language = Locale.US
                Log.d("TTS", "TextToSpeech initialized")
            } else {
                Log.e("TTS", "Failed to initialize TextToSpeech")
            }
        }

    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // No-op; we won't rely on events here
    }

    override fun onInterrupt() {
        // No-op
    }

    /**
     * Schedules a tap to occur [delayMs] milliseconds in the future.
     * This allows the app to minimize first.
     */
    fun scheduleTapOutsideApp(x: Int, y: Int, delayMs: Long) {
        Handler(Looper.getMainLooper()).postDelayed({
            Toast.makeText(
                this,
                "Performing TAP at ($x, $y) outside app",
                Toast.LENGTH_SHORT
            ).show()
            performTap(x, y)
        }, delayMs)
    }

    /**
     * Schedules a swipe to occur [delayMs] milliseconds in the future.
     * This allows the app to minimize first.
     */
    fun scheduleSwipeOutsideApp(x1: Int, y1: Int, x2: Int, y2: Int, delayMs: Long) {
        Handler(Looper.getMainLooper()).postDelayed({
            Toast.makeText(
                this,
                "Performing SWIPE from ($x1, $y1) to ($x2, $y2) outside app",
                Toast.LENGTH_SHORT
            ).show()
            performSwipe(x1, y1, x2, y2)
        }, delayMs)
    }

    fun performTyping(fullText: String, delayMs: Long = 0) {
        Handler(Looper.getMainLooper()).postDelayed({
            val rootNode = rootInActiveWindow ?: return@postDelayed

            val focusedNode = rootNode.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)

            if (focusedNode != null && focusedNode.isEditable) {
                val args = Bundle().apply {
                    putCharSequence(
                        AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
                        fullText
                    )
                }
                focusedNode.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)

                Toast.makeText(this, "Pasted: $fullText", Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(this, "No editable field focused", Toast.LENGTH_SHORT).show()
            }
        }, delayMs)
    }



    // -------------------------------------------------
    // Internal methods to dispatch actual gestures
    // -------------------------------------------------

    private fun performTap(x: Int, y: Int) {
        Log.d("ActionAccessibilityService", "performTap($x, $y)")
        val path = Path().apply {
            moveTo(x.toFloat(), y.toFloat())
        }
        val stroke = GestureDescription.StrokeDescription(path, 0, 100)
        val gesture = GestureDescription.Builder().addStroke(stroke).build()
        dispatchGesture(gesture, null, null)
    }

    private fun performSwipe(x1: Int, y1: Int, x2: Int, y2: Int) {
        Log.d("ActionAccessibilityService", "performSwipe($x1, $y1, $x2, $y2)")
        val path = Path().apply {
            moveTo(x1.toFloat(), y1.toFloat())
            lineTo(x2.toFloat(), y2.toFloat())
        }
        val stroke = GestureDescription.StrokeDescription(path, 0, 300)
        val gesture = GestureDescription.Builder().addStroke(stroke).build()
        dispatchGesture(gesture, null, null)
    }
}
