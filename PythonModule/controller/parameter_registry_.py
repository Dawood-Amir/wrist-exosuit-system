# parameter_registry.py
PARAMETER_REGISTRY = {
    # -------------------------------------------------------------------------
    # POSITION CONTROL PARAMETERS
    # -------------------------------------------------------------------------
    'position_kp': {
        'type': 'float',
        'min': 0.5,
        'max': 15.0,
        'default': 8.0,
        'units': 'N·m/rad',
        'description': 'Position control stiffness gain. '
                       'Higher = stiffer, more responsive movement. '
                       'Lower = softer, more compliant movement.',
        'config_key': 'position_kp'
    },
    
    'position_kd': {
        'type': 'float',
        'min': 0.01,
        'max': 3.0,
        'default': 0.8,
        'units': 'N·m·s/rad',
        'description': 'Position control damping gain. '
                       'Higher = more damping, smoother movement. '
                       'Lower = less damping, faster response.',
        'config_key': 'position_kd'
    },
    
    'movement_speed': {
        'type': 'float',
        'min': 0.1,
        'max': 2.0,
        'default': 0.8,
        'units': 'none',
        'description': 'Overall movement speed scaling. '
                       'Lower = slower, more controlled movements. '
                       'Higher = faster, more responsive movements.',
        'config_key': 'movement_speed'
    },

    # -------------------------------------------------------------------------
    # SAFETY PARAMETERS (Keep these - essential for position control)
    # -------------------------------------------------------------------------
    'max_velocity': {
        'type': 'float',
        'min': 0.5,
        'max': 10.0,
        'default': 4.0,
        'units': 'rad/s',
        'description': 'Maximum motor velocity for safety. '
                       'Prevents dangerously fast movements.',
        'config_key': 'max_velocity'
    },
    
    'upper_position_limit': {
        'type': 'float',
        'min': 0.5,
        'max': 2.5,
        'default': 1.8,
        'units': 'rad',
        'description': 'Upper position limit to prevent over-extension. '
                       'Maximum extension angle.',
        'config_key': 'upper_position_limit'
    },
    
    'lower_position_limit': {
        'type': 'float',
        'min': -2.5,
        'max': -0.5,
        'default': -1.8,
        'units': 'rad',
        'description': 'Lower position limit to prevent over-flexion. '
                       'Maximum flexion angle.',
        'config_key': 'lower_position_limit'
    },

    # -------------------------------------------------------------------------
    # MOVEMENT STRENGTH PARAMETERS (Adapted for position control)
    # -------------------------------------------------------------------------
    'extension_strength_scale': {
        'type': 'float', 
        'min': 0.3,
        'max': 1.5,
        'default': 1.0,
        'units': 'none',
        'description': 'Scales extension movement range based on EMG input. '
                       'Higher = larger extension movements for same EMG signal.',
        'config_key': 'extension_strength_scale'
    },
    
    'flexion_strength_scale': {
        'type': 'float',
        'min': 0.3,
        'max': 1.5,
        'default': 1.0,
        'units': 'none',
        'description': 'Scales flexion movement range based on EMG input. '
                       'Higher = larger flexion movements for same EMG signal.',
        'config_key': 'flexion_strength_scale'
    },

    'min_movement_threshold': {
        'type': 'float',
        'min': 0.05,
        'max': 0.3,
        'default': 0.1,
        'units': 'none',
        'description': 'Minimum EMG strength required to start movement. '
                       'Prevents small muscle twitches from triggering motion.',
        'config_key': 'min_movement_threshold'
    },

    # -------------------------------------------------------------------------
    # COMFORT & SMOOTHING PARAMETERS
    # -------------------------------------------------------------------------
    'smoothing_factor': {
        'type': 'float',
        'min': 0.01,
        'max': 0.3,
        'default': 0.05,
        'units': 'none',
        'description': 'Smoothing factor for position commands. '
                       'Higher = smoother but slower response. '
                       'Lower = faster but potentially jerky.',
        'config_key': 'smoothing_factor'
    },

    'deadzone_threshold': {
        'type': 'float',
        'min': 0.0,
        'max': 0.2,
        'default': 0.05,
        'units': 'rad',
        'description': 'Small movements below this threshold are ignored. '
                       'Reduces jitter around neutral position.',
        'config_key': 'deadzone_threshold'
    }
}

# def map_android_to_registry(self, android_key):
#     android_to_registry = {
#         # Position control parameters
#         'positionKp': 'position_kp',
#         'positionKd': 'position_kd', 
#         'movementSpeed': 'movement_speed',
        
#         # Safety parameters
#         'maxVelocity': 'max_velocity',
#         'upperPositionLimit': 'upper_position_limit',
#         'lowerPositionLimit': 'lower_position_limit',
        
#         # Strength scaling
#         'extensionStrengthScale': 'extension_strength_scale',
#         'flexionStrengthScale': 'flexion_strength_scale',
#         'minMovementThreshold': 'min_movement_threshold',
        
#         # Comfort parameters
#         'smoothingFactor': 'smoothing_factor',
#         'deadzoneThreshold': 'deadzone_threshold'
#     }
#     return android_to_registry.get(android_key, android_key)