package com.exosuit.exo

import android.Manifest
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.exosuit.exo.composables.GuidedRecordingScreen
import com.exosuit.exo.composables.MotorControlScreen
import com.exosuit.exo.composables.TrainingProgressScreen

class MainActivity : ComponentActivity() {
    private val emgViewModel: EmgViewModel by viewModels()
    private val motorViewModel: MotorViewModel by viewModels()

    // Launcher for permission requests
    private val requestPermissionsLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        // Check if all required permissions are granted
        val allGranted = permissions.all { it.value }
        emgViewModel.setPermissionsGranted(allGranted)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Request permissions on launch
        requestPermissionsLauncher.launch(
            arrayOf(
                Manifest.permission.BLUETOOTH_SCAN,
                Manifest.permission.BLUETOOTH_CONNECT,
                Manifest.permission.ACCESS_FINE_LOCATION // needed for BLE scan
            )
        )

        setContent {
            val navController = rememberNavController()
            NavHost(navController = navController, startDestination = NavGraph.Screen.EmgHome.route) {
                composable(NavGraph.Screen.EmgHome.route) {
                    EmgScreen(emgViewModel,
                        applicationContext ,
                        navController ,motorViewModel)
                }
                composable("motor_settings") {
                    MotorControlScreen( navController ,motorViewModel)
                }


                composable(NavGraph.Screen.GuidedRecording.route) {
                    GuidedRecordingScreen(emgViewModel, navController)
                }
                composable("training_progress_screen") {
                    TrainingProgressScreen(viewModel = emgViewModel, navController = navController)
                }
            }
        }

    }

 /*   override fun onDestroy() {
        super.onDestroy()
        if(isFinishing){
            UdpMotorController.getInstance().shutdownController()
        }
    }
    */

}


