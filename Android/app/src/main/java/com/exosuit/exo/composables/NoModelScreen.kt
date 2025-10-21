package com.exosuit.exo.composables


import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Science
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.ncorti.myonnaise.MyoStatus




// NoModelScreen
@Composable
fun NoModelScreen(
    myoStatus: MyoStatus,
    permissionsGranted: Boolean,
    onScanMyo: () -> Unit,
    onStartTraining: () -> Unit,
    onCheckModels: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(
            imageVector =  Icons.Outlined.Science,
            contentDescription = "No Model",
            modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.primary
        )

        Spacer(modifier = Modifier.height(24.dp))

        Text(
            "No Model Found",
            style = MaterialTheme.typography.titleLarge,
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            "Please connect your Myo armband to start training a new model",
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(32.dp))

        // Add button to check for models
        Button(
            onClick = onCheckModels,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Check for Existing Models")
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Myo Connection Status
        when (myoStatus) {
            MyoStatus.CONNECTING -> {
                CircularProgressIndicator()
                Spacer(modifier = Modifier.height(16.dp))
                Text("Connecting to Myo...", color = Color.Gray)
            }
            MyoStatus.CONNECTED, MyoStatus.READY -> {
                Text("Myo Connected ✓", color = Color.Green)
                Spacer(modifier = Modifier.height(24.dp))
                Button(
                    onClick = onStartTraining,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Start Training Session")
                }
            }
            MyoStatus.DISCONNECTED -> {
                Button(
                    onClick = onScanMyo,
                    enabled = permissionsGranted,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Scan for Myo Armband")
                }

                if (!permissionsGranted) {
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        "Please grant Bluetooth permissions to scan for Myo",
                        color = Color.Red,
                        textAlign = TextAlign.Center
                    )
                }
            }
        }
    }
}


