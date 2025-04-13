package com.example.bitcampproject

import android.app.Activity
import android.content.Context
import android.util.Log
import android.widget.Toast
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import org.json.JSONObject

class MyWebSocketListener(
    private val context: Context,
    private val promptText: String
) : WebSocketListener() {

    override fun onOpen(webSocket: WebSocket, response: Response) {
        val activity = context as Activity
        activity.runOnUiThread {
            // Put the activity in the background
            activity.moveTaskToBack(true)

            // Delay slightly to ensure we have a screenshot
            android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                val screenshotB64 = ScreenCaptureService.latestScreenshotBase64
                if (screenshotB64 != null) {
                    // Send prompt + screenshot on open
                    val json = JSONObject().apply {
                        put("prompt", promptText)
                        put("imageb64", screenshotB64)
                    }
                    webSocket.send(json.toString())
                } else {
                    Toast.makeText(context, "Screenshot capture failed.", Toast.LENGTH_SHORT).show()
                }
            }, 4000)
        }
    }

    override fun onMessage(webSocket: WebSocket, text: String) {
        Log.d("WebSocket", "onMessage (text): $text")
        (context as Activity).runOnUiThread {
            Toast.makeText(context, "Server said: $text", Toast.LENGTH_SHORT).show()

            try {
                val json = JSONObject(text)
                val isDone = json.getBoolean("isDone")
                if (isDone) {
                    // Close when server signals completion
                    webSocket.close(1000, "Task completed by server")
                    Toast.makeText(context, "WebSocket Closing.", Toast.LENGTH_SHORT).show()
                    return@runOnUiThread
                }

                // Sample parse of "command" object
                val commandObj = json.getJSONObject("command")
                val action = commandObj.getString("action")

                // Handle swipe gestures
                when (action) {
                    "swipeUp" -> {
                        ActionAccessibilityService.instance?.scheduleSwipeOutsideApp(
                            600, 2000, 600, 800, 0
                        )
                    }
                    "swipeDown" -> {
                        ActionAccessibilityService.instance?.scheduleSwipeOutsideApp(
                            600, 800, 600, 2000, 0
                        )
                    }
                    "swipeLeft" -> {
                        ActionAccessibilityService.instance?.scheduleSwipeOutsideApp(
                            800, 1200, 200, 1200, 0
                        )
                    }
                    "swipeRight" -> {
                        ActionAccessibilityService.instance?.scheduleSwipeOutsideApp(
                            200, 1200, 800, 1200, 0
                        )
                    }
                    "tap" -> {
                        // Example tap at the center of the screen
                        val x = commandObj.getInt("x_cord")
                        val y = commandObj.getInt("y_cord")
                        ActionAccessibilityService.instance?.scheduleTapOutsideApp(x, y, 0)
                    }
                    "type" -> {
                        val x = commandObj.getInt("x_cord")
                        val y = commandObj.getInt("y_cord")

                        val rawText = commandObj.getString("text")
                        val textToType = rawText.trim('"', '\'')

                        // First tap to focus the input field, then type after delay
                        ActionAccessibilityService.instance?.scheduleTapOutsideApp(x, y, 0)
                        ActionAccessibilityService.instance?.performTyping(textToType, 1000)  // delay allows tap to register
                    }
                    "back" -> {
                        ActionAccessibilityService.instance?.scheduleSwipeOutsideApp(
                            0, 1200, 400, 1200, 0
                        )
                    }

                    "announce" -> {
                        val message = commandObj.optString("text", "")
                        if (message.isNotEmpty()) {
                            ActionAccessibilityService.instance?.speak(message)
                        }
                    }
                }

                // After performing an action, send back updated screenshot only
                android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                    val screenshotB64 = ScreenCaptureService.latestScreenshotBase64
                    if (screenshotB64 != null) {
                        val responseJson = JSONObject().apply {
                            put("imageb64", screenshotB64)
                        }
                        webSocket.send(responseJson.toString())
                    }
                }, 4000)

            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
        Log.d("WebSocket", "onMessage (bytes): $bytes")
    }

    override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
        Log.d("WebSocket", "onClosing: $code / $reason")
        webSocket.close(1000, null)
        (context as Activity).runOnUiThread {
            Toast.makeText(context, "WebSocket Closing: $reason", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
        Log.e("WebSocket", "onFailure", t)
        (context as Activity).runOnUiThread {
            Toast.makeText(context, "WebSocket Failure: ${t.message}", Toast.LENGTH_LONG).show()
        }
    }
}
