package com.example.bitcampproject

import android.os.Bundle
import android.widget.ImageView
import androidx.appcompat.app.AppCompatActivity
import com.bumptech.glide.Glide

class Screen1Activity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.screen1)

        val imgWave = findViewById<ImageView>(R.id.imgWave)

        Glide.with(this)
            .asGif()
            .load(R.raw.wave)
            .into(imgWave)

        imgWave.scaleX = 8f
        imgWave.scaleY = 8f

    }
}
