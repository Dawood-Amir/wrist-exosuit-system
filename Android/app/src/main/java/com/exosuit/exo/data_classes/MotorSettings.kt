package com.exosuit.exo.data_classes

import org.json.JSONObject

data class MotorSettings(
    // Position control parameters
    val positionKp: Float = 8.0f,
    val positionKd: Float = 0.8f,
    val movementSpeed: Float = 0.8f,

    // Safety limits
    val maxVelocity: Float = 4.0f,
    val upperPositionLimit: Float = 1.8f,
    val lowerPositionLimit: Float = -1.8f,

    // Strength scaling parameters
    val extensionStrengthScale: Float = 1.0f,
    val flexionStrengthScale: Float = 1.0f,
    val minMovementThreshold: Float = 0.1f,

    // Comfort parameters
    val smoothingFactor: Float = 0.05f,
    val deadzoneThreshold: Float = 0.05f
) {
    companion object {
        // Position control parameters
        const val POSITION_KP_MIN = 0.5f
        const val POSITION_KP_MAX = 15.0f
        const val POSITION_KP_DEFAULT = 8.0f

        const val POSITION_KD_MIN = 0.01f
        const val POSITION_KD_MAX = 3.0f
        const val POSITION_KD_DEFAULT = 0.8f

        const val MOVEMENT_SPEED_MIN = 0.1f
        const val MOVEMENT_SPEED_MAX = 2.0f
        const val MOVEMENT_SPEED_DEFAULT = 0.8f

        // Safety limits
        const val MAX_VELOCITY_MIN = 0.5f
        const val MAX_VELOCITY_MAX = 10.0f
        const val MAX_VELOCITY_DEFAULT = 4.0f

        const val UPPER_POSITION_LIMIT_MIN = 0.5f
        const val UPPER_POSITION_LIMIT_MAX = 2.5f
        const val UPPER_POSITION_LIMIT_DEFAULT = 1.8f

        const val LOWER_POSITION_LIMIT_MIN = -2.5f
        const val LOWER_POSITION_LIMIT_MAX = -0.5f
        const val LOWER_POSITION_LIMIT_DEFAULT = -1.8f

        // Strength scaling
        const val EXTENSION_STRENGTH_SCALE_MIN = 0.3f
        const val EXTENSION_STRENGTH_SCALE_MAX = 1.5f
        const val EXTENSION_STRENGTH_SCALE_DEFAULT = 1.0f

        const val FLEXION_STRENGTH_SCALE_MIN = 0.3f
        const val FLEXION_STRENGTH_SCALE_MAX = 1.5f
        const val FLEXION_STRENGTH_SCALE_DEFAULT = 1.0f

        const val MIN_MOVEMENT_THRESHOLD_MIN = 0.05f
        const val MIN_MOVEMENT_THRESHOLD_MAX = 0.3f
        const val MIN_MOVEMENT_THRESHOLD_DEFAULT = 0.1f

        // Comfort parameters
        const val SMOOTHING_FACTOR_MIN = 0.01f
        const val SMOOTHING_FACTOR_MAX = 0.3f
        const val SMOOTHING_FACTOR_DEFAULT = 0.05f

        const val DEADZONE_THRESHOLD_MIN = 0.0f
        const val DEADZONE_THRESHOLD_MAX = 0.2f
        const val DEADZONE_THRESHOLD_DEFAULT = 0.05f
    }

    fun toJson(): String {
        return JSONObject().apply {
            put("positionKp", positionKp)
            put("positionKd", positionKd)
            put("movementSpeed", movementSpeed)
            put("maxVelocity", maxVelocity)
            put("upperPositionLimit", upperPositionLimit)
            put("lowerPositionLimit", lowerPositionLimit)
            put("extensionStrengthScale", extensionStrengthScale)
            put("flexionStrengthScale", flexionStrengthScale)
            put("minMovementThreshold", minMovementThreshold)
            put("smoothingFactor", smoothingFactor)
            put("deadzoneThreshold", deadzoneThreshold)
        }.toString()
    }
}