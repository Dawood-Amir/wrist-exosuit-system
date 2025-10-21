package com.exosuit.exo.composables

import android.widget.Toast
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.ExperimentalAnimationApi
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.animateIntAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.with
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.exosuit.exo.EmgViewModel
import com.exosuit.exo.data_classes.ModelType
import kotlinx.coroutines.delay




@OptIn(ExperimentalAnimationApi::class)
@Composable
fun GuidedRecordingScreen(viewModel: EmgViewModel, navController: NavController) {
    val steps = viewModel.recordingStepsList
    var currentStepIndex by remember { mutableStateOf(0) }
    val currentStep = steps.getOrNull(currentStepIndex)
    var timerMs by remember { mutableStateOf(currentStep?.durationMs ?: 5000L) }
    var isPaused by remember { mutableStateOf(false) }
    var hasStarted by remember { mutableStateOf(false) }
    var countdownMs by remember { mutableStateOf(3000L) } // 3-second countdown
    var stepStarted by remember { mutableStateOf(false) }
    val context = LocalContext.current
    val haptic = LocalHapticFeedback.current

    var showTrainingChoiceDialog by remember { mutableStateOf(false) }
    var recordedDataPath by remember { mutableStateOf<String?>(null) }


    // Animate timer and progress
    val animatedProgress by animateFloatAsState(
        targetValue = if (countdownMs > 0) 0f else 1f - timerMs.toFloat() / (currentStep?.durationMs ?: 5000L),
        animationSpec = tween(durationMillis = 100, easing = LinearEasing), label = ""
    )

    val animatedTimer by animateIntAsState(
        targetValue = if (countdownMs > 0) ((countdownMs + 999) / 1000).toInt() else ((timerMs + 999) / 1000).toInt(),
        animationSpec = tween(durationMillis = 100, easing = LinearEasing), label = ""
    )

    // Pulsing glow animation
    val pulseAnim by rememberInfiniteTransition().animateFloat(
        initialValue = 0.9f,
        targetValue = 1.2f,
        animationSpec = infiniteRepeatable(
            animation = tween(800, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ), label = ""
    )

    if (!hasStarted) {
        Column(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text("Ready to start recording", style = MaterialTheme.typography.titleLarge)
            Spacer(modifier = Modifier.height(16.dp))
            Button(onClick = {
                hasStarted = true
                viewModel.startSessionRecording()
            }) { Text("Start") }
        }
    } else {
        AnimatedContent(targetState = currentStepIndex, transitionSpec = {
            fadeIn(animationSpec = tween(300)) with fadeOut(animationSpec = tween(300))
        }, label = "") { stepIndex ->
            val step = steps.getOrNull(stepIndex)
            if (stepIndex >= steps.size) {
                // Session completed - show options
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(24.dp),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        "Recording Complete!",
                        style = MaterialTheme.typography.titleLarge
                    )
                    Spacer(modifier = Modifier.height(24.dp))

                    Button(
                        onClick = {
                            viewModel.stopRecording { success, path ->
                                if (success) {
                                    recordedDataPath = path
                                    showTrainingChoiceDialog = true
                                } else {
                                    Toast.makeText(context, "Failed to save data", Toast.LENGTH_SHORT).show()
                                }

                              /*  if (success) {
                                    // Send data to Python server for training
                                    viewModel.sendDataToTrainingServer(path)
                                    navController.navigate("training_progress_screen")
                                } else {
                                    Toast.makeText(context, "Failed to save data", Toast.LENGTH_SHORT).show()
                                }*/
                            }
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Save Data and Train Model")
                    }

                    if (showTrainingChoiceDialog && recordedDataPath != null) {
                        AlertDialog(
                            onDismissRequest = { showTrainingChoiceDialog = false },
                            title = { Text("Choose Model Type") },
                            text = {
                                Column {
                                    Text("Which model type do you want to train?")
                                    Spacer(modifier = Modifier.height(16.dp))
                                    Button(
                                        onClick = {
                                            viewModel.trainingModelType = ModelType.RIDGE_FOR_EXO
                                            viewModel.sendDataToTrainingServer(recordedDataPath!!)
                                            showTrainingChoiceDialog = false
                                            navController.navigate("training_progress_screen")
                                        },
                                        modifier = Modifier.fillMaxWidth()
                                    ) { Text("Train Ridge Model") }

                                    Spacer(modifier = Modifier.height(8.dp))
                                    Button(
                                        onClick = {
                                            viewModel.trainingModelType = ModelType.TFLITE
                                            viewModel.sendDataToTrainingServer(recordedDataPath!!)
                                            showTrainingChoiceDialog = false
                                            navController.navigate("training_progress_screen")
                                        },
                                        modifier = Modifier.fillMaxWidth()
                                    ) { Text("Train MLP Model") }
                                }
                            },
                            confirmButton = {},
                            dismissButton = {
                                Button(onClick = { showTrainingChoiceDialog = false }) { Text("Cancel") }
                            }
                        )
                    }



                    Spacer(modifier = Modifier.height(16.dp))

                    Button(
                        onClick = {
                            viewModel.stopRecording { success, path ->
                                if (success) {
                                    Toast.makeText(context, "Data saved to $path", Toast.LENGTH_SHORT).show()
                                    navController.popBackStack()
                                }
                            }
                        },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(containerColor = Color.Gray)
                    ) {
                        Text("Save Data Only")
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    Button(
                        onClick = {
                            viewModel.stopRecording { _, _ -> }
                            navController.popBackStack()
                        },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(containerColor = Color.Red)
                    ) {
                        Text("Discard Data")
                    }
                }
            } else {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(24.dp),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        "Step ${stepIndex + 1}/${steps.size}: ${step?.label ?: "Done"}",
                        style = MaterialTheme.typography.titleLarge,
                        color = if (!isPaused) MaterialTheme.colorScheme.primary else Color.Gray
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Box(contentAlignment = Alignment.Center) {
                        if (!isPaused) {
                            Box(
                                modifier = Modifier
                                    .size(150.dp * pulseAnim)
                                    .background(
                                        color = MaterialTheme.colorScheme.primary.copy(alpha = 0.2f),
                                        shape = CircleShape
                                    )
                            )
                        }
                        CircularProgressIndicator(
                            progress = animatedProgress,
                            strokeWidth = 8.dp,
                            modifier = Modifier.size(150.dp),
                            color = if (!isPaused) MaterialTheme.colorScheme.primary else Color.Gray
                        )
                        Text(
                            if (countdownMs > 0) "$animatedTimer" else "$animatedTimer s",
                            style = MaterialTheme.typography.headlineMedium,
                            color = if (!isPaused) MaterialTheme.colorScheme.onBackground else Color.Gray
                        )
                    }
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        if (countdownMs > 0) "Get ready..." else "Hold the hand in position...",
                        style = MaterialTheme.typography.bodyMedium
                    )
                    Spacer(modifier = Modifier.height(24.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        Button(onClick = {
                            isPaused = !isPaused
                            if (isPaused) {
                                viewModel.pauseRecording()
                            } else {
                                // Only resume recording if we're past the countdown phase
                                if (countdownMs <= 0) {
                                    viewModel.resumeRecording()
                                }
                            }
                        }) {
                            Text(if (isPaused) "Resume" else "Pause")
                        }
                        Button(onClick = {
                            // Skip current step safely
                            viewModel.pauseRecording()
                            isPaused = false
                            stepStarted = false
                            currentStepIndex++
                            timerMs = steps.getOrNull(currentStepIndex)?.durationMs ?: 5000L
                            countdownMs = 3000L
                            haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                        }) {
                            Text("Skip")
                        }
                    }
                }
            }
        }

        // Timer logic with countdown
        LaunchedEffect(currentStepIndex, hasStarted) {
            if (!hasStarted) return@LaunchedEffect
            val step = steps.getOrNull(currentStepIndex) ?: return@LaunchedEffect
            if (stepStarted) return@LaunchedEffect
            stepStarted = true

            countdownMs = 3000L
            timerMs = step.durationMs

            // Countdown
            while (countdownMs > 0) {
                if (!isPaused) {
                    delay(100L)
                    countdownMs -= 100L
                } else {
                    delay(100L)
                }
            }

            // Start recording only if not paused
            if (!isPaused) {
                step.targetValue?.let { viewModel.setLabel(it) }
                viewModel.startRecording()
            }

            var remaining = step.durationMs
            while (remaining > 0) {
                if (!isPaused) {
                    delay(100L)
                    remaining -= 100L
                    timerMs = remaining.coerceAtLeast(0)
                } else {
                    delay(100L)
                }
            }

            // Pause recording at end of step
            viewModel.pauseRecording()
            haptic.performHapticFeedback(HapticFeedbackType.LongPress)

            // Move to next step automatically
            currentStepIndex++
            stepStarted = false
        }
    }
}

