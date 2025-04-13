package com.example.bitcampproject

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.widget.Toast

class ActionAccessibilityService : AccessibilityService() {

    companion object {
        // Holds a reference to this service if it's running
        var instance: ActionAccessibilityService? = null
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
    }

    override fun onDestroy() {
        super.onDestroy()
        instance = null
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        Toast.makeText(this, "Accessibility Service Connected", Toast.LENGTH_SHORT).show()
        Log.d("ActionAccessibilityService", "onServiceConnected()")
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
