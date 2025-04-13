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
            val now = SystemClock.uptimeMillis()
            if (movieStart == 0L) movieStart = now

            val relTime = ((now - movieStart) % it.duration()).toInt()
            it.setTime(relTime)

            val scaleX = 800f / it.width()
            val scaleY = 800f / it.height()

            canvas.save()
            canvas.scale(scaleX, scaleY)
            it.draw(canvas, 0f, 0f)
            canvas.restore()

            invalidate() // keep redrawing for animation
        }
    }
}
