package com.example.bitcampproject  // ⬅ Replace with your actual package

import android.content.Context
import android.graphics.Canvas
import android.graphics.Movie
import android.os.SystemClock
import android.util.AttributeSet
import android.view.View
import com.example.bitcampproject.R  // required for R.raw.wave

class GifView(context: Context, attrs: AttributeSet?) : View(context, attrs) {

    private var movie: Movie? = null
    private var movieStart: Long = 0

    init {
        val inputStream = context.resources.openRawResource(R.raw.wave)
        movie = Movie.decodeStream(inputStream)
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        movie?.let {
            val now = android.os.SystemClock.uptimeMillis()
            if (movieStart == 0L) movieStart = now

            val relTime = ((now - movieStart) % it.duration()).toInt()
            it.setTime(relTime)

            // Center and scale the GIF to fit inside the view
            val scaleX = width.toFloat() / it.width()
            val scaleY = height.toFloat() / it.height()
            val scale = minOf(scaleX, scaleY)

            val dx = (width - it.width() * scale) / 2
            val dy = (height - it.height() * scale) / 2

            canvas.save()
            canvas.translate(dx, dy)
            canvas.scale(scale, scale)
            it.draw(canvas, 0f, 0f)
            canvas.restore()

            invalidate()
        }
    }

}