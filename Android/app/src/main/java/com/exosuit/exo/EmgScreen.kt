package com.exosuit.exo

import android.annotation.SuppressLint
import android.content.Context
import android.widget.Toast
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BluetoothDisabled
import androidx.compose.material.icons.filled.Cable
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.ModelTraining
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Start
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.navigation.NavHostController
import com.exosuit.exo.composables.MotorStatusIndicator
import com.exosuit.exo.composables.NoModelScreen
import com.exosuit.exo.data_classes.ModelType
import com.exosuit.exo.utility.UdpMotorController
import com.ncorti.myonnaise.MyoStatus
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin


val ExoSuitBlue = Color(0xFF6E59A8)
val ExoSuitGreen = Color(0xFF4CAF50)
val ExoSuitRed = Color(0xFFF44336)
val ExoSuitInactiveGray = Color(0xFFBDBDBD)
val ExoSuitSurface = Color(0xFFF5F5F5)

@SuppressLint("MissingPermission")
@Composable
fun EmgScreen(viewModel: EmgViewModel, context: Context,
              navController: NavHostController,
              motorViewModel: MotorViewModel
) {

    val motorConnectionState by motorViewModel.connectionState.collectAsState()
    val isRecording by viewModel.isRecording
    val predicted by viewModel.predictedValue
    val smoothedAngle by viewModel.smoothedAngle.collectAsState()
    val wristFlexion by animateFloatAsState(targetValue = smoothedAngle, label = "wristFlexionAnimation")

    val myoStatus by viewModel.myoStatus.collectAsState()
    val modelExists by viewModel.modelExists.collectAsState()

    var showMyoDialog by remember { mutableStateOf(false) }
    var showModelChoiceDialog by remember { mutableStateOf(false) }
    val availableMyos by viewModel.availableMyos.collectAsState()
    val availableModels by viewModel.availableModels.collectAsState()
    val selectedModel by viewModel.selectedModel.collectAsState()
    val modelActive by viewModel.modelActive.collectAsState()

    var showModelSelectionDialog by remember { mutableStateOf(false) }
    var vizExpanded by remember { mutableStateOf(true) } // Start expanded by default

    LaunchedEffect(Unit) { viewModel.checkModelExists() }

    // --- UI START ---

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = ExoSuitSurface
    ) {
        if (modelExists == true) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {

                // --- 1. HEADER & STATUS ---
                Text(
                    "Exosuit Controller",
                    style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.SemiBold),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 16.dp, top = 8.dp)
                )

                // Connectivity/Status Card
                Card(
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {

                        }
                        /*Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                "SYSTEM STATUS",
                                style = MaterialTheme.typography.labelMedium,
                                color = Color.Gray
                            )
                            // Start System Button (Updated Look)
                            Button(
                                onClick = {
                                    motorViewModel.sendStartSignal { _, _ -> *//* logic unchanged *//* }
                                },
                                enabled = motorConnectionState == UdpMotorController.ConnectionState.READY_TO_START,
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = if (motorConnectionState == UdpMotorController.ConnectionState.READY_TO_START) ExoSuitGreen else ExoSuitInactiveGray
                                )
                            ) {
                                Icon(Icons.Default.Start, contentDescription = "Start", modifier = Modifier.size(18.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("START SYSTEM")
                            }
                        }*/
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                "SYSTEM STATUS",
                                style = MaterialTheme.typography.labelMedium,
                                color = Color.Gray
                            )

                            // Show Disconnect button when connected, Start button when ready to start
                            if (motorConnectionState == UdpMotorController.ConnectionState.CONNECTED) {
                                Button(
                                    onClick = {
                                        motorViewModel.sendDisconnectSignal { success, error ->

                                           /* if (success) {
                                                Toast.makeText(context, "Motors disconnected", Toast.LENGTH_SHORT).show()
                                            } else {
                                                Toast.makeText(context, "Disconnect failed: $error", Toast.LENGTH_SHORT).show()
                                            }*/
                                        }
                                    },
                                    colors = ButtonDefaults.buttonColors(containerColor = ExoSuitRed)
                                ) {
                                    Icon(Icons.Default.Stop, contentDescription = "Disconnect", modifier = Modifier.size(18.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text("DISCONNECT")
                                }
                            } else {
                                Button(
                                    onClick = {
                                        motorViewModel.sendStartSignal { success, error ->
                                            /*if (success) {
                                                Toast.makeText(context, "System started", Toast.LENGTH_SHORT).show()
                                            } else {
                                                Toast.makeText(context, "Start failed: $error", Toast.LENGTH_SHORT).show()
                                            }*/
                                        }
                                    },
                                    enabled = motorConnectionState == UdpMotorController.ConnectionState.READY_TO_START,
                                    colors = ButtonDefaults.buttonColors(
                                        containerColor = if (motorConnectionState == UdpMotorController.ConnectionState.READY_TO_START) ExoSuitGreen else ExoSuitInactiveGray
                                    )
                                ) {
                                    Icon(Icons.Default.Start, contentDescription = "Start", modifier = Modifier.size(18.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text("START SYSTEM")
                                }
                            }
                        }

                        Divider(modifier = Modifier.padding(vertical = 8.dp))

                        // Motor Status Indicator
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Cable, contentDescription = "Motor", tint = ExoSuitBlue)
                            Spacer(modifier = Modifier.width(8.dp))
                            MotorStatusIndicator(motorConnectionState)
                        }

                        // Myo Status Indicator
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            val myoIndicatorColor = when (myoStatus) {
                                MyoStatus.CONNECTED, MyoStatus.READY -> ExoSuitGreen
                                MyoStatus.CONNECTING -> ExoSuitBlue
                                MyoStatus.DISCONNECTED -> ExoSuitRed
                            }
                            Box(
                                modifier = Modifier
                                    .size(10.dp)
                                    .background(myoIndicatorColor, CircleShape)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                "Myo Status: ${myoStatus.name}",
                                color = myoIndicatorColor,
                                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold)
                            )
                        }



                        // Motor Settings Button
                        Spacer(modifier = Modifier.height(8.dp))
                        OutlinedButton(
                            onClick = { navController.navigate("motor_settings") },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = ExoSuitBlue)
                        ) {
                            Icon(Icons.Default.Settings, contentDescription = "Motor Settings", modifier = Modifier.size(20.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("MOTOR SETTINGS")
                        }

                    }
                }

                // --- 2. VISUALIZATION ---


                /*Card(
                    modifier = Modifier.fillMaxWidth().height(360.dp).padding(bottom = 16.dp), // Increased height slightly for the header
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
                ) {
                    Column(modifier = Modifier.fillMaxSize()) {

                        // 🌟 Add the Header Row 🌟
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 16.dp, vertical = 8.dp) // Padding for the header content
                        ) {
                            Text(
                                "Real-Time Exosuit View", // <-- The descriptive title
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                                color = ExoSuitBlue
                            )
                            Divider(modifier = Modifier.padding(top = 4.dp), color = Color.LightGray)
                        }

                        // The Visualization Canvas
                        ArmCanvas(
                            wristFlexion = wristFlexion,
                            radialDeviation = 0f,
                            cableTension = 20f,
                            modifier = Modifier
                                .fillMaxSize() // Fill the remaining space
                                .padding(8.dp)
                        )
                    }
                }*/


                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        // Use fixed height only when expanded, otherwise wrap content
                        .height(if (vizExpanded) 360.dp else Dp.Unspecified)
                        .padding(bottom = 16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
                ) {
                    Column(modifier = Modifier.fillMaxSize()) {

                        // --- HEADER (Always visible and clickable) ---
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { vizExpanded = !vizExpanded } //  Toggle state on click
                                .padding(horizontal = 16.dp, vertical = 12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                "Real-Time Exosuit View",
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                                color = ExoSuitBlue,
                                modifier = Modifier.weight(1f)
                            )
                            Icon(
                                imageVector = if (vizExpanded) Icons.Default.KeyboardArrowUp else Icons.Default.KeyboardArrowDown,
                                contentDescription = if (vizExpanded) "Collapse view" else "Expand view",
                                tint = Color.Gray
                            )
                        }

                        // --- Visible only when expanded ---
                        if (vizExpanded) {
                            Divider(modifier = Modifier.padding(horizontal = 16.dp), color = Color.LightGray)

                            // The Visualization Canvas
                            ArmCanvas(
                                wristFlexion = wristFlexion,
                                radialDeviation = 0f,
                                cableTension = 20f,
                                modifier = Modifier
                                    .fillMaxSize() // Fill the remaining height
                                    .padding(8.dp)
                            )
                        }
                    }
                }

                // --- 3. MODEL & PREDICTED VALUES ---
                Card(
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp), // Increased bottom padding slightly
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            "MODEL OUTPUT",
                            style = MaterialTheme.typography.labelMedium,
                            color = Color.Gray
                        )
                        Divider(modifier = Modifier.padding(vertical = 8.dp))

                        // Predicted Values
                        Text(
                            "Predicted Values:",
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.SemiBold
                        )
                        val modelTypeLabel = when (viewModel.activeModelType) {
                            ModelType.TFLITE -> "TFLite"
                            else -> "Ridge"
                        }
                        Text(
                            "[%s]".format(
                                predicted.joinToString(", ") { "%.3f".format(it) }
                            ),
                            style = MaterialTheme.typography.titleMedium,
                            color = ExoSuitBlue
                        )

                        Spacer(modifier = Modifier.height(16.dp))

                        // Model Details, Selection Button, and Activation Switch
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            // Column for Model Details - uses weight to constrain space
                            Column(
                                modifier = Modifier.weight(1f) // 👈 FIX 1: Use weight to make the text take available space
                            ) {
                                Text(
                                    "Active Model:",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = Color.Gray
                                )
                                Text(
                                    "${selectedModel ?: "None"} ($modelTypeLabel)",
                                    style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold),
                                    color = if (selectedModel != null) ExoSuitGreen else ExoSuitInactiveGray,
                                    maxLines = 1, // Ensures text stays on one line
                                    overflow = TextOverflow.Ellipsis // Truncates if too long
                                )
                            }

                            // Group for Switch and "Activate" text
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                modifier = Modifier.padding(start = 8.dp)
                            ) {
                                Text(
                                    "Activate",
                                    style = MaterialTheme.typography.bodyMedium,
                                    modifier = Modifier.padding(end = 4.dp) // Reduced end padding
                                )
                                Switch(
                                    checked = modelActive,
                                    onCheckedChange = { viewModel.toggleModelActive(it) },
                                    enabled = selectedModel != null,
                                    colors = SwitchDefaults.colors(
                                        checkedThumbColor = Color.White,
                                        checkedTrackColor = ExoSuitGreen
                                    )
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(12.dp))

                        // Select Model Button (now full width below the details)
                        Button(
                            onClick = { showModelSelectionDialog = true },
                            enabled = availableModels.isNotEmpty(),
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(containerColor = ExoSuitBlue)
                        ) {
                            Icon(Icons.Default.ModelTraining, contentDescription = "Select Model", modifier = Modifier.size(20.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("CHANGE / SELECT MODEL")
                        }
                    }
                }


                // --- 4. TRAINING AND PERIPHERAL CONTROLS ---
                Card(
                    modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            "TOOLS & SETUP",
                            style = MaterialTheme.typography.labelMedium,
                            color = Color.Gray
                        )
                        Divider(modifier = Modifier.padding(vertical = 8.dp))

                        // Training Button
                        Button(
                            onClick = { navController.navigate(NavGraph.Screen.GuidedRecording.route) },
                            enabled = !isRecording && myoStatus == MyoStatus.READY,
                            modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = ExoSuitBlue)
                        ) {
                            Icon(Icons.Default.ModelTraining, contentDescription = "Start Training", modifier = Modifier.size(20.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("START NEW TRAINING")
                        }

                        // Myo Band Control
                        when (myoStatus) {
                            MyoStatus.CONNECTING -> {
                                showMyoDialog = false
                                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                                    CircularProgressIndicator(Modifier.size(24.dp))
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text("Connecting to Myo...", color = Color.Gray)
                                }
                            }

                            MyoStatus.CONNECTED, MyoStatus.READY -> {
                                OutlinedButton(
                                    onClick = { viewModel.disconnectMyo() },
                                    modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
                                    colors = ButtonDefaults.outlinedButtonColors(contentColor = ExoSuitRed),
                                    border = BorderStroke(1.dp, ExoSuitRed)
                                ) {
                                    Icon(Icons.Default.BluetoothDisabled, contentDescription = "Disconnect Myo", modifier = Modifier.size(20.dp))
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text("DISCONNECT MYO")
                                }
                            }

                            MyoStatus.DISCONNECTED -> {
                                Button(
                                    onClick = { viewModel.scanForMyos(); showMyoDialog = true },
                                    enabled = viewModel.permissionsGranted.value,
                                    modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = ExoSuitGreen)
                                ) {
                                    Icon(Icons.Default.Search, contentDescription = "Scan Myo Bands", modifier = Modifier.size(20.dp))
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text("SCAN FOR MYO BANDS")
                                }

                                if (!viewModel.permissionsGranted.value) {
                                    Text(
                                        "Grant Bluetooth and location permissions to scan.",
                                        color = ExoSuitRed,
                                        style = MaterialTheme.typography.bodySmall
                                    )
                                }
                            }
                        }


                    }
                }
            }
        } else {

            NoModelScreen(
                myoStatus = myoStatus,
                permissionsGranted = viewModel.permissionsGranted.value,
                onScanMyo = { viewModel.scanForMyos(); showMyoDialog = true },
                onStartTraining = { navController.navigate(NavGraph.Screen.GuidedRecording.route) },
                onCheckModels = { viewModel.checkModelExists() }
            )
        }
    }

    // --- DIALOGS (Existing Logic Retained) ---
    // Model Selection Dialog
    if (showModelSelectionDialog) {
        AlertDialog(
            onDismissRequest = { showModelSelectionDialog = false },
            title = { Text("Select Model") },
            text = {
                Column {
                    if (availableModels.isEmpty()) Text("No models available")
                    else {
                        availableModels.forEach { modelName ->
                            val typeLabel = when {
                                modelName.endsWith(".tflite") -> "TFLite"
                                modelName.contains("_hybrid_") -> "Hybrid"
                                else -> "Ridge"
                            }
                            Button(
                                onClick = {

                                    when (typeLabel) {
                                        "TFLite" -> {
                                            viewModel.loadTfliteInterpreter(modelName)
                                            viewModel.activeModelType = ModelType.TFLITE
                                        }

                                        else -> {
                                            viewModel.loadModel(modelName)
                                            viewModel.activeModelType = ModelType.RIDGE_FOR_EXO
                                        }
                                    }
                                    showModelSelectionDialog = false
                                    Toast.makeText(
                                        context,
                                        "$typeLabel model $modelName loaded",
                                        Toast.LENGTH_SHORT
                                    ).show()
                                },
                                modifier = Modifier.fillMaxWidth()
                            ) { Text("$modelName ($typeLabel)") }
                            Spacer(modifier = Modifier.height(4.dp))
                        }
                    }
                }
            },
            confirmButton = {
                Button(onClick = { showModelSelectionDialog = false }) { Text("Cancel") }
            }
        )
    }

    // Model Choice Dialog
    if (showModelChoiceDialog) {
        AlertDialog(
            onDismissRequest = { showModelChoiceDialog = false },
            title = { Text("Model Found") },
            text = {
                Column {
                    Text("${availableModels.size} model(s) found. Would you like to select one?")
                    Spacer(modifier = Modifier.height(8.dp))
                    availableModels.forEach { modelName ->
                        val typeLabel = when {
                            modelName.endsWith(".tflite") -> "TFLite"
                            modelName.contains("_hybrid_") -> "Hybrid"
                            else -> "Ridge"
                        }
                        Button(
                            onClick = {

                                when (typeLabel) {
                                    "TFLite" -> {
                                        viewModel.loadTfliteInterpreter(modelName)
                                        viewModel.activeModelType = ModelType.TFLITE
                                    }

                                    else -> {
                                        viewModel.loadModel(modelName)
                                        viewModel.activeModelType = ModelType.RIDGE_FOR_EXO
                                    }
                                }
                                showModelChoiceDialog = false
                                Toast.makeText(context, "$typeLabel model $modelName loaded", Toast.LENGTH_SHORT).show()
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) { Text("$modelName ($typeLabel)") }
                        Spacer(modifier = Modifier.height(4.dp))
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (availableModels.isNotEmpty()) {
                            val firstModel = availableModels.first()
                            if (firstModel.endsWith(".tflite")) {
                                viewModel.loadTfliteInterpreter(firstModel)
                                viewModel.activeModelType = ModelType.TFLITE
                            } else {
                                viewModel.loadModel(firstModel)
                                viewModel.activeModelType = ModelType.RIDGE_FOR_EXO
                            }
                            Toast.makeText(context, "Model $firstModel loaded", Toast.LENGTH_SHORT).show()
                        }
                        showModelChoiceDialog = false
                    }
                ) { Text("Use First Model") }
            },
            dismissButton = {
                Button(
                    onClick = {
                        showModelChoiceDialog = false
                        Toast.makeText(context, "You can select a model later", Toast.LENGTH_SHORT).show()
                    }
                ) { Text("Select Later") }
            }
        )
    }

    // Myo Selection Dialog
    if (showMyoDialog) {
        Dialog(onDismissRequest = { showMyoDialog = false }) {
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = MaterialTheme.colorScheme.surface,
                modifier = Modifier
                    .fillMaxWidth()
                    .fillMaxHeight(0.6f)
            ) {
                Column(
                    modifier = Modifier
                        .padding(16.dp)
                        .fillMaxHeight()
                ) {
                    Text("Select a Myo Band", style = MaterialTheme.typography.titleMedium)
                    Spacer(modifier = Modifier.height(8.dp))

                    Box(modifier = Modifier.weight(1f)) {
                        if (availableMyos.isEmpty()) Text("Scanning...")
                        else LazyColumn {
                            items(availableMyos) { device ->
                                val displayName = device.name?.takeIf { it.isNotBlank() } ?: device.address
                                Button(
                                    onClick = {
                                        viewModel.connectToMyo(
                                            device,
                                            onConnected = {
                                                showMyoDialog = false
                                                Toast.makeText(
                                                    context,
                                                    "Connected to $displayName",
                                                    Toast.LENGTH_SHORT
                                                ).show()
                                            },
                                            onConnecting = { showMyoDialog = false },
                                            onError = { err ->
                                                showMyoDialog = false
                                                Toast.makeText(
                                                    context,
                                                    "Failed to connect: ${err.message}",
                                                    Toast.LENGTH_LONG
                                                ).show()
                                            }
                                        )
                                    },
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(vertical = 4.dp)
                                ) { Text(displayName) }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedButton(
                        onClick = { viewModel.scanForMyos() },
                        modifier = Modifier.fillMaxWidth()
                    ) { Text("Retry Scan") }
                }
            }
        }
    }
}



@Composable
fun ArmCanvas(
    wristFlexion: Float,     // wrist flexion in degrees (-45 to 45)
    radialDeviation: Float,
    cableTension: Float,
    modifier: Modifier = Modifier
) {
    // Validate inputs to prevent NaN values
    val safeWristFlexion = if (wristFlexion.isNaN() || wristFlexion.isInfinite()) 0f else wristFlexion
    val safeRadialDeviation = if (radialDeviation.isNaN() || radialDeviation.isInfinite()) 0f else radialDeviation
    val safeCableTension = if (cableTension.isNaN() || cableTension.isInfinite()) 0f else cableTension

    Canvas(modifier = modifier) {
        val canvasWidth = size.width
        val canvasHeight = size.height

        val shoulder = Offset(canvasWidth * 0.5f, canvasHeight * 0.2f)

        val upperArmLength = canvasHeight * 0.3f
        val forearmLength = canvasHeight * 0.25f
        val handLength = canvasHeight * 0.2f

        val initialUpperArmAngle = 18f
        val initialElbowAngle = 36f
        val initialWristFlexion = 36f

        val upperArmAngleRad = Math.toRadians(initialUpperArmAngle.toDouble())
        val combinedAngleRad = Math.toRadians((initialUpperArmAngle + initialElbowAngle).toDouble())

        // Draw shoulder
        drawCircle(
            color = Color(0xFF3F51B5),
            center = shoulder,
            radius = 20f
        )

        val elbow = Offset(
            shoulder.x + upperArmLength * sin(upperArmAngleRad).toFloat(),
            shoulder.y + upperArmLength * cos(upperArmAngleRad).toFloat()
        )

        drawLine(
            color = Color(0xFF3F51B5),
            start = shoulder,
            end = elbow,
            strokeWidth = 30f,
            cap = StrokeCap.Round
        )

        drawCircle(
            color = Color(0xFF3F51B5),
            center = elbow,
            radius = 15f
        )

        val wristBase = Offset(
            elbow.x + forearmLength * sin(combinedAngleRad).toFloat(),
            elbow.y + forearmLength * cos(combinedAngleRad).toFloat()
        )

        val wrist = Offset(
            wristBase.x + safeRadialDeviation * (forearmLength / 30f),
            wristBase.y
        )

        drawLine(
            color = Color(0xFF2196F3),
            start = elbow,
            end = wrist,
            strokeWidth = 25f,
            cap = StrokeCap.Round
        )

        drawCircle(
            color = Color(0xFF2196F3),
            center = wrist,
            radius = 25f
        )

        val forearmVector = wrist - elbow
        val forearmAngle = atan2(forearmVector.x, forearmVector.y)

        val totalWristAngle = initialWristFlexion + safeWristFlexion
        val handAngle = forearmAngle + totalWristAngle * (Math.PI / 180f).toFloat()

        // Validate handAngle to prevent NaN values
        val safeHandAngle = if (handAngle.isNaN() || handAngle.isInfinite()) 0f else handAngle

        val hand = Offset(
            wrist.x + handLength * sin(safeHandAngle),
            wrist.y + handLength * cos(safeHandAngle)
        )

        // Only draw if hand position is valid
        if (!hand.x.isNaN() && !hand.y.isNaN()) {
            drawLine(
                color = Color(0xFF4CAF50),
                start = wrist,
                end = hand,
                strokeWidth = 30f,
                cap = StrokeCap.Round
            )

            // Draw cables
            val cableCount = 3
            val cableColor = when {
                safeCableTension > 45f -> Color.Red
                safeCableTension > 35f -> Color.Yellow
                else -> Color(0xFFFF9800)
            }
            val cableWidth = 3f + (safeCableTension / 50f) * 5f

            for (i in 0 until cableCount) {
                val cableStart = Offset(
                    shoulder.x + (i - 1) * 15f,
                    shoulder.y
                )

                drawLine(
                    color = cableColor,
                    start = cableStart,
                    end = hand,
                    strokeWidth = cableWidth,
                    pathEffect = PathEffect.dashPathEffect(
                        intervals = floatArrayOf(10f, 5f),
                        phase = 0f
                    )
                )
            }

            val isCritical = abs(totalWristAngle) > 75f || abs(safeRadialDeviation) > 25f
            val circleColor = if (isCritical) Color.Red else Color(0xFF4CAF50)
            val circleRadius = 25f

            drawCircle(
                color = circleColor,
                center = hand,
                radius = circleRadius
            )

            if (isCritical) {
                drawCircle(
                    color = Color.Red.copy(alpha = 0.3f),
                    center = hand,
                    radius = circleRadius * 1.5f
                )
            }
        }
    }
}