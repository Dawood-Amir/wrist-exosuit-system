package com.exosuit.exo.data_classes

data class RecordingStep(
    val label: String,
    val targetValue: List<Float> ,// Labels
    val durationMs: Long = 5000L // default 5 seconds

)
