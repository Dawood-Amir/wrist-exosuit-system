package com.exosuit.exo.composables

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.exosuit.exo.EmgViewModel
import com.exosuit.exo.NavGraph
import kotlinx.coroutines.delay


@Composable
fun TrainingProgressScreen(viewModel: EmgViewModel, navController: NavController) {
    val trainingProgress by viewModel.trainingProgress.collectAsState()
    val trainingStatus by viewModel.trainingStatus.collectAsState()

    val modelReady by viewModel.modelReady.collectAsState()

    LaunchedEffect(modelReady) {
        if (modelReady) {
            navController.navigate(NavGraph.Screen.EmgHome.route) {
                popUpTo(NavGraph.Screen.GuidedRecording.route) { inclusive = true }
            }
        }
    }

    // Determine if Retry button should show
    val showRetry = trainingStatus.contains("Error", ignoreCase = true) ||
            trainingStatus.contains("timeout", ignoreCase = true) ||
            trainingStatus.contains("Failed", ignoreCase = true) ||
            trainingStatus.startsWith("SERVER_ERROR", ignoreCase = true)

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            "Training Model",
            style = MaterialTheme.typography.titleLarge
        )

        Spacer(modifier = Modifier.height(32.dp))

        // Fixed CircularProgressIndicator - Material3 version
        CircularProgressIndicator(
            progress = trainingProgress / 100f,
            modifier = Modifier.size(100.dp),
            strokeWidth = 8.dp
        )

        Spacer(modifier = Modifier.height(24.dp))

        Text("$trainingProgress%")

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            trainingStatus,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(32.dp))

        if (trainingProgress == 100) {
            Button(
                onClick = { navController.popBackStack() }
            ) {
                Text("Done")
            }
        } else {
            // Back to Home button always visible on failure
            if (showRetry) {
                Button(
                    onClick = {
                        navController.navigate(NavGraph.Screen.EmgHome.route) {
                            popUpTo(NavGraph.Screen.GuidedRecording.route) { inclusive = true }
                        }
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Back to Home")
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Retry button
               /* Button(
                    onClick = {
                        viewModel.lastRecordedDataPath?.let { path ->
                            viewModel.retryTraining(path)
                        }
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Retry")
                }*/
            }
        }
    }


    // Automatically go back when training is complete
    if (trainingProgress == 100) {
        LaunchedEffect(Unit) {
            delay(2000) // Show success message for 2 seconds
            navController.popBackStack()
        }
    }
}
