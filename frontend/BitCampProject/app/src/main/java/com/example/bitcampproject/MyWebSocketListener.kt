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
            }, 1500)
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
                            600, 1800, 600, 1000, 0
                        )
                    }
                    "swipeDown" -> {
                        ActionAccessibilityService.instance?.scheduleSwipeOutsideApp(
                            600, 1000, 600, 1800, 0
                        )
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
                }, 1500)

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
