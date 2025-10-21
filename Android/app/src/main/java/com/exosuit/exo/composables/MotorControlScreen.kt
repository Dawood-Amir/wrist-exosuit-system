package com.exosuit.exo.composables

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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
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
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.exosuit.exo.MotorViewModel
import com.exosuit.exo.data_classes.MotorSettings

@Composable
fun MotorControlScreen(
    navController: NavHostController? = null,
    viewModel: MotorViewModel
) {
    val motorSettings by viewModel.motorSettings.collectAsState()

    var uiState by remember {
        mutableStateOf(
            MotorUiState.fromMotorSettings(motorSettings)
        )
    }
    var isLocked by remember { mutableStateOf(false) }

    LaunchedEffect(motorSettings) {
        uiState = MotorUiState.fromMotorSettings(motorSettings)
    }

    Box(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 16.dp),
        ) {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Spacer(modifier = Modifier.height(10.dp))
                LockSwitchCard(isLocked, onLockChange = { isLocked = it })

                Text(
                    text = "Position Control Settings",
                    style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Bold),
                    modifier = Modifier.padding(top = 8.dp),
                    color = MaterialTheme.colorScheme.primary
                )
            }

            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                SettingsCards(uiState, isLocked) { newUiState ->
                    uiState = newUiState
                }

                item {
                    Spacer(modifier = Modifier.height(80.dp))
                }
            }
        }

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomCenter)
        ) {
            val surfaceColor = MaterialTheme.colorScheme.surface
            val gradientHeight = 32.dp

            Spacer(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(gradientHeight)
                    .background(
                        Brush.verticalGradient(
                            colorStops = arrayOf(
                                0.0f to surfaceColor.copy(alpha = 0.0f),
                                1.0f to surfaceColor.copy(alpha = 1.0f)
                            )
                        )
                    )
            )

            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(surfaceColor)
                    .padding(horizontal = 16.dp)
                    .padding(vertical = 16.dp)
            ) {
                SaveButton(
                    isLocked = isLocked,
                    onClick = {
                        viewModel.updateMotorSettings(uiState.toMotorSettings())
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(50.dp)
                )
                Spacer(modifier = Modifier.height(4.dp))
            }
        }
    }
}

private fun LazyListScope.SettingsCards(
    uiState: MotorUiState,
    isLocked: Boolean,
    onUiStateChange: (MotorUiState) -> Unit
) {
    item {
        PositionControlCard(
            positionKp = uiState.positionKp,
            onPositionKpChange = { onUiStateChange(uiState.copy(positionKp = it)) },
            positionKd = uiState.positionKd,
            onPositionKdChange = { onUiStateChange(uiState.copy(positionKd = it)) },
            movementSpeed = uiState.movementSpeed,
            onMovementSpeedChange = { onUiStateChange(uiState.copy(movementSpeed = it)) },
            enabled = !isLocked
        )
    }

    item {
        SafetyLimitsCard(
            maxVelocity = uiState.maxVelocity,
            onMaxVelocityChange = { onUiStateChange(uiState.copy(maxVelocity = it)) },
            upperPositionLimit = uiState.upperPositionLimit,
            onUpperPositionLimitChange = { onUiStateChange(uiState.copy(upperPositionLimit = it)) },
            lowerPositionLimit = uiState.lowerPositionLimit,
            onLowerPositionLimitChange = { onUiStateChange(uiState.copy(lowerPositionLimit = it)) },
            enabled = !isLocked
        )
    }

    item {
        StrengthScalingCard(
            extensionStrengthScale = uiState.extensionStrengthScale,
            onExtensionStrengthScaleChange = { onUiStateChange(uiState.copy(extensionStrengthScale = it)) },
            flexionStrengthScale = uiState.flexionStrengthScale,
            onFlexionStrengthScaleChange = { onUiStateChange(uiState.copy(flexionStrengthScale = it)) },
            minMovementThreshold = uiState.minMovementThreshold,
            onMinMovementThresholdChange = { onUiStateChange(uiState.copy(minMovementThreshold = it)) },
            enabled = !isLocked
        )
    }

    item {
        ComfortParametersCard(
            smoothingFactor = uiState.smoothingFactor,
            onSmoothingFactorChange = { onUiStateChange(uiState.copy(smoothingFactor = it)) },
            deadzoneThreshold = uiState.deadzoneThreshold,
            onDeadzoneThresholdChange = { onUiStateChange(uiState.copy(deadzoneThreshold = it)) },
            enabled = !isLocked
        )
    }
}

data class MotorUiState(
    val positionKp: Float = MotorSettings.POSITION_KP_DEFAULT,
    val positionKd: Float = MotorSettings.POSITION_KD_DEFAULT,
    val movementSpeed: Float = MotorSettings.MOVEMENT_SPEED_DEFAULT,
    val maxVelocity: Float = MotorSettings.MAX_VELOCITY_DEFAULT,
    val upperPositionLimit: Float = MotorSettings.UPPER_POSITION_LIMIT_DEFAULT,
    val lowerPositionLimit: Float = MotorSettings.LOWER_POSITION_LIMIT_DEFAULT,
    val extensionStrengthScale: Float = MotorSettings.EXTENSION_STRENGTH_SCALE_DEFAULT,
    val flexionStrengthScale: Float = MotorSettings.FLEXION_STRENGTH_SCALE_DEFAULT,
    val minMovementThreshold: Float = MotorSettings.MIN_MOVEMENT_THRESHOLD_DEFAULT,
    val smoothingFactor: Float = MotorSettings.SMOOTHING_FACTOR_DEFAULT,
    val deadzoneThreshold: Float = MotorSettings.DEADZONE_THRESHOLD_DEFAULT
) {
    companion object {
        fun fromMotorSettings(settings: MotorSettings): MotorUiState {
            return MotorUiState(
                positionKp = settings.positionKp,
                positionKd = settings.positionKd,
                movementSpeed = settings.movementSpeed,
                maxVelocity = settings.maxVelocity,
                upperPositionLimit = settings.upperPositionLimit,
                lowerPositionLimit = settings.lowerPositionLimit,
                extensionStrengthScale = settings.extensionStrengthScale,
                flexionStrengthScale = settings.flexionStrengthScale,
                minMovementThreshold = settings.minMovementThreshold,
                smoothingFactor = settings.smoothingFactor,
                deadzoneThreshold = settings.deadzoneThreshold
            )
        }
    }

    fun toMotorSettings(): MotorSettings {
        return MotorSettings(
            positionKp = positionKp,
            positionKd = positionKd,
            movementSpeed = movementSpeed,
            maxVelocity = maxVelocity,
            upperPositionLimit = upperPositionLimit,
            lowerPositionLimit = lowerPositionLimit,
            extensionStrengthScale = extensionStrengthScale,
            flexionStrengthScale = flexionStrengthScale,
            minMovementThreshold = minMovementThreshold,
            smoothingFactor = smoothingFactor,
            deadzoneThreshold = deadzoneThreshold
        )
    }
}

@Composable
fun PositionControlCard(
    positionKp: Float,
    onPositionKpChange: (Float) -> Unit,
    positionKd: Float,
    onPositionKdChange: (Float) -> Unit,
    movementSpeed: Float,
    onMovementSpeedChange: (Float) -> Unit,
    enabled: Boolean = true
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(4.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "Position Control",
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(bottom = 8.dp)
            )
            SettingSlider(
                label = "Stiffness (Kp)",
                value = positionKp,
                onValueChange = onPositionKpChange,
                range = MotorSettings.POSITION_KP_MIN..MotorSettings.POSITION_KP_MAX,
                enabled = enabled,
                decimalPlaces = 1
            )
            SettingSlider(
                label = "Damping (Kd)",
                value = positionKd,
                onValueChange = onPositionKdChange,
                range = MotorSettings.POSITION_KD_MIN..MotorSettings.POSITION_KD_MAX,
                enabled = enabled,
                decimalPlaces = 2
            )
            SettingSlider(
                label = "Movement Speed",
                value = movementSpeed,
                onValueChange = onMovementSpeedChange,
                range = MotorSettings.MOVEMENT_SPEED_MIN..MotorSettings.MOVEMENT_SPEED_MAX,
                enabled = enabled,
                decimalPlaces = 2
            )
        }
    }
}

@Composable
fun SafetyLimitsCard(
    maxVelocity: Float,
    onMaxVelocityChange: (Float) -> Unit,
    upperPositionLimit: Float,
    onUpperPositionLimitChange: (Float) -> Unit,
    lowerPositionLimit: Float,
    onLowerPositionLimitChange: (Float) -> Unit,
    enabled: Boolean = true
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(4.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "Safety Limits",
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(bottom = 8.dp)
            )
            SettingSlider(
                label = "Max Velocity (rad/s)",
                value = maxVelocity,
                onValueChange = onMaxVelocityChange,
                range = MotorSettings.MAX_VELOCITY_MIN..MotorSettings.MAX_VELOCITY_MAX,
                enabled = enabled,
                decimalPlaces = 1
            )
            SettingSlider(
                label = "Upper Position Limit (rad)",
                value = upperPositionLimit,
                onValueChange = onUpperPositionLimitChange,
                range = MotorSettings.UPPER_POSITION_LIMIT_MIN..MotorSettings.UPPER_POSITION_LIMIT_MAX,
                enabled = enabled,
                decimalPlaces = 2
            )
            SettingSlider(
                label = "Lower Position Limit (rad)",
                value = lowerPositionLimit,
                onValueChange = onLowerPositionLimitChange,
                range = MotorSettings.LOWER_POSITION_LIMIT_MIN..MotorSettings.LOWER_POSITION_LIMIT_MAX,
                enabled = enabled,
                decimalPlaces = 2
            )
        }
    }
}

@Composable
fun StrengthScalingCard(
    extensionStrengthScale: Float,
    onExtensionStrengthScaleChange: (Float) -> Unit,
    flexionStrengthScale: Float,
    onFlexionStrengthScaleChange: (Float) -> Unit,
    minMovementThreshold: Float,
    onMinMovementThresholdChange: (Float) -> Unit,
    enabled: Boolean = true
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(4.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "Strength Scaling",
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(bottom = 8.dp)
            )
            SettingSlider(
                label = "Extension Strength Scale",
                value = extensionStrengthScale,
                onValueChange = onExtensionStrengthScaleChange,
                range = MotorSettings.EXTENSION_STRENGTH_SCALE_MIN..MotorSettings.EXTENSION_STRENGTH_SCALE_MAX,
                enabled = enabled,
                decimalPlaces = 2
            )
            SettingSlider(
                label = "Flexion Strength Scale",
                value = flexionStrengthScale,
                onValueChange = onFlexionStrengthScaleChange,
                range = MotorSettings.FLEXION_STRENGTH_SCALE_MIN..MotorSettings.FLEXION_STRENGTH_SCALE_MAX,
                enabled = enabled,
                decimalPlaces = 2
            )
            SettingSlider(
                label = "Min Movement Threshold",
                value = minMovementThreshold,
                onValueChange = onMinMovementThresholdChange,
                range = MotorSettings.MIN_MOVEMENT_THRESHOLD_MIN..MotorSettings.MIN_MOVEMENT_THRESHOLD_MAX,
                enabled = enabled,
                decimalPlaces = 2
            )
        }
    }
}

@Composable
fun ComfortParametersCard(
    smoothingFactor: Float,
    onSmoothingFactorChange: (Float) -> Unit,
    deadzoneThreshold: Float,
    onDeadzoneThresholdChange: (Float) -> Unit,
    enabled: Boolean = true
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(4.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "Comfort Parameters",
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(bottom = 8.dp)
            )
            SettingSlider(
                label = "Smoothing Factor",
                value = smoothingFactor,
                onValueChange = onSmoothingFactorChange,
                range = MotorSettings.SMOOTHING_FACTOR_MIN..MotorSettings.SMOOTHING_FACTOR_MAX,
                enabled = enabled,
                decimalPlaces = 2
            )
            SettingSlider(
                label = "Deadzone Threshold (rad)",
                value = deadzoneThreshold,
                onValueChange = onDeadzoneThresholdChange,
                range = MotorSettings.DEADZONE_THRESHOLD_MIN..MotorSettings.DEADZONE_THRESHOLD_MAX,
                enabled = enabled,
                decimalPlaces = 2
            )
        }
    }
}

@Composable
fun LockSwitchCard(isLocked: Boolean, onLockChange: (Boolean) -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(4.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = "Lock Controls",
                style = MaterialTheme.typography.titleMedium
            )
            Switch(
                checked = isLocked,
                onCheckedChange = onLockChange,
                colors = SwitchDefaults.colors(
                    checkedThumbColor = MaterialTheme.colorScheme.error,
                    checkedTrackColor = MaterialTheme.colorScheme.errorContainer,
                    uncheckedThumbColor = MaterialTheme.colorScheme.primary,
                    uncheckedTrackColor = MaterialTheme.colorScheme.primaryContainer
                )
            )
        }
    }
}

@Composable
fun SaveButton(
    isLocked: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Button(
        onClick = onClick,
        enabled = !isLocked,
        colors = ButtonDefaults.buttonColors(
            containerColor = MaterialTheme.colorScheme.primary,
            contentColor = MaterialTheme.colorScheme.onPrimary,
            disabledContainerColor = MaterialTheme.colorScheme.surfaceVariant,
            disabledContentColor = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f)
        ),
        modifier = modifier
            .fillMaxWidth()
            .height(50.dp)
    ) {
        Text(
            "Save and Apply",
            style = MaterialTheme.typography.labelLarge,
            color = if (isLocked) MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f)
            else MaterialTheme.colorScheme.onPrimary
        )
    }
}

@Composable
private fun SettingSlider(
    label: String,
    value: Float,
    onValueChange: (Float) -> Unit,
    range: ClosedFloatingPointRange<Float>,
    decimalPlaces: Int = 2,
    enabled: Boolean = true,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier.padding(vertical = 8.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = label,
                style = MaterialTheme.typography.bodyLarge,
                color = if (enabled) MaterialTheme.colorScheme.onBackground
                else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
            )
            Text(
                text = "%.${decimalPlaces}f".format(value),
                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                color = if (enabled) MaterialTheme.colorScheme.primary
                else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
            )
        }
        Slider(
            value = value,
            onValueChange = onValueChange,
            valueRange = range,
            enabled = enabled,
            modifier = Modifier.fillMaxWidth(),
            colors = SliderDefaults.colors(
                thumbColor = if (enabled) MaterialTheme.colorScheme.primary
                else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f),
                activeTrackColor = if (enabled) MaterialTheme.colorScheme.primary
                else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f),
                inactiveTrackColor = MaterialTheme.colorScheme.surfaceVariant
            )
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = "%.${decimalPlaces}f".format(range.start),
                style = MaterialTheme.typography.bodySmall
            )
            Text(
                text = "%.${decimalPlaces}f".format(range.endInclusive),
                style = MaterialTheme.typography.bodySmall
            )
        }
    }
}
