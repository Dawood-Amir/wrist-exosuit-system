package com.exosuit.exo.composables

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.exosuit.exo.utility.UdpMotorController



@Composable
fun MotorStatusIndicator(connectionState: UdpMotorController.ConnectionState) {
    val (color, statusText) = when(connectionState) {
        UdpMotorController.ConnectionState.DISCONNECTED -> Pair(Color.Gray, "Disconnected")
        UdpMotorController.ConnectionState.SETTINGS_SENT -> Pair(Color.Yellow, "Settings Sent")
        UdpMotorController.ConnectionState.READY_TO_START -> Pair(Color.Blue, "Ready to Start")
        UdpMotorController.ConnectionState.CONNECTED -> Pair(Color.Green, "Connected")
        UdpMotorController.ConnectionState.ERROR -> Pair(Color.Red, "Error")
    }

    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier
    ) {
        Text(
            text = "Exosuit Status:",
            style = MaterialTheme.typography.bodyMedium,
            color = Color.Black
        )
        Box(
            modifier = Modifier
                .size(16.dp)
                .background(color, shape = CircleShape)
        )
        Text(
            text = statusText,
            color = color,
            style = MaterialTheme.typography.bodyMedium
        )
    }
}