package com.exosuit.exo

import android.app.Application
import android.content.Context
import android.util.Log
import android.widget.Toast
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.exosuit.exo.data_classes.MotorSettings
import com.exosuit.exo.utility.UdpMotorController
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MotorViewModel(application: Application) : AndroidViewModel(application) {
    private val udpController = UdpMotorController.getInstance(viewModelScope , getApplication())

    private val _motorSettings = MutableStateFlow(MotorSettings())
    val motorSettings: StateFlow<MotorSettings> = _motorSettings

    private val sharedPreferences = application.getSharedPreferences("MotorControlPrefs", Context.MODE_PRIVATE)

    val connectionState: StateFlow<UdpMotorController.ConnectionState>
        get() = udpController.connectionState


    init {
        viewModelScope.launch(Dispatchers.IO) {
            loadMotorSettings()
        }
    }

    fun updateMotorSettings(newSettings: MotorSettings) {
        _motorSettings.value = newSettings
        saveMotorSettings(newSettings)

        udpController.sendMotorSettings(getApplication(), newSettings) { success, error ->

            viewModelScope.launch {
                withContext(Dispatchers.Main) {
                    if (!success) {
                        Log.e("MyoScan", "Failed to send settings: $error")
                        Toast.makeText(
                            getApplication(), "Failed to send settings: $error", Toast.LENGTH_SHORT
                        ).show()
                    } else {
                        Toast.makeText(
                            getApplication(), "Motor Setting sent", Toast.LENGTH_SHORT
                        ).show()
                    }
                }
            }
        }
    }
    fun sendStartSignal(onComplete: (Boolean, String?) -> Unit) {
        udpController.sendStartSignal(getApplication(), onComplete)
    }



    fun saveMotorSettings(settings: MotorSettings) {
        sharedPreferences.edit().apply {
            // Position control parameters
            putFloat("positionKp", settings.positionKp)
            putFloat("positionKd", settings.positionKd)
            putFloat("movementSpeed", settings.movementSpeed)

            // Safety limits
            putFloat("maxVelocity", settings.maxVelocity)
            putFloat("upperPositionLimit", settings.upperPositionLimit)
            putFloat("lowerPositionLimit", settings.lowerPositionLimit)

            // Strength scaling
            putFloat("extensionStrengthScale", settings.extensionStrengthScale)
            putFloat("flexionStrengthScale", settings.flexionStrengthScale)
            putFloat("minMovementThreshold", settings.minMovementThreshold)

            // Comfort parameters
            putFloat("smoothingFactor", settings.smoothingFactor)
            putFloat("deadzoneThreshold", settings.deadzoneThreshold)
            apply()
        }
        _motorSettings.value = settings.copy()
    }

    fun sendDisconnectSignal(onComplete: (Boolean, String?) -> Unit) {
        udpController.sendDisconnectSignal(getApplication(), onComplete)
    }
    fun loadMotorSettings() {
        val loadedSettings = MotorSettings(
            // Position control parameters
            positionKp = sharedPreferences.getFloat("positionKp", MotorSettings.POSITION_KP_DEFAULT),
            positionKd = sharedPreferences.getFloat("positionKd", MotorSettings.POSITION_KD_DEFAULT),
            movementSpeed = sharedPreferences.getFloat("movementSpeed", MotorSettings.MOVEMENT_SPEED_DEFAULT),

            // Safety limits
            maxVelocity = sharedPreferences.getFloat("maxVelocity", MotorSettings.MAX_VELOCITY_DEFAULT),
            upperPositionLimit = sharedPreferences.getFloat("upperPositionLimit", MotorSettings.UPPER_POSITION_LIMIT_DEFAULT),
            lowerPositionLimit = sharedPreferences.getFloat("lowerPositionLimit", MotorSettings.LOWER_POSITION_LIMIT_DEFAULT),

            // Strength scaling
            extensionStrengthScale = sharedPreferences.getFloat("extensionStrengthScale", MotorSettings.EXTENSION_STRENGTH_SCALE_DEFAULT),
            flexionStrengthScale = sharedPreferences.getFloat("flexionStrengthScale", MotorSettings.FLEXION_STRENGTH_SCALE_DEFAULT),
            minMovementThreshold = sharedPreferences.getFloat("minMovementThreshold", MotorSettings.MIN_MOVEMENT_THRESHOLD_DEFAULT),

            // Comfort parameters
            smoothingFactor = sharedPreferences.getFloat("smoothingFactor", MotorSettings.SMOOTHING_FACTOR_DEFAULT),
            deadzoneThreshold = sharedPreferences.getFloat("deadzoneThreshold", MotorSettings.DEADZONE_THRESHOLD_DEFAULT)
        )

        _motorSettings.value = loadedSettings
    }

}