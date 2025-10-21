# validation_utils.py
from parameter_registry_ import PARAMETER_REGISTRY

def validate_parameter(parameter_name, value):
    """Validate a parameter against registry with comprehensive checks"""
    if parameter_name not in PARAMETER_REGISTRY:
        raise ValueError(f"Unknown parameter: {parameter_name}")
    
    meta = PARAMETER_REGISTRY[parameter_name]
    
    # Type validation
    if meta['type'] == 'float' and not isinstance(value, (int, float)):
        raise TypeError(f"Parameter {parameter_name} must be numeric")
    
    # Range validation
    if value < meta['min']:
        print(f"Warning: {parameter_name} ({value}) below minimum ({meta['min']}). Using minimum.")
        return meta['min']
    
    if value > meta['max']:
        print(f"Warning: {parameter_name} ({value}) exceeds maximum ({meta['max']}). Using maximum.")
        return meta['max']
    
    return value

def get_safe_default(parameter_name):
    """Get safe default value for a parameter"""
    if parameter_name not in PARAMETER_REGISTRY:
        raise ValueError(f"Unknown parameter: {parameter_name}")
    return PARAMETER_REGISTRY[parameter_name]['default']

def get_parameter_config_key(parameter_name):
    """Get corresponding config.json key for a parameter"""
    if parameter_name not in PARAMETER_REGISTRY:
        return None
    return PARAMETER_REGISTRY[parameter_name].get('config_key')