from datetime import datetime
from typing import Any


def validate_is_primitive(value: Any):
    if not isinstance(value, (datetime, str, float, int, bool, type(None))):
        raise TypeError(f"Structure contains non-primitive value of type {type(value).__name__}.")

def validate_primitive_dict(d: dict):
    """ Validate that all base-level elements within a dictionary are primitive values. """
    for key, value in d.items():
        # Validate key
        validate_is_primitive(key)

        # Validate value
        if isinstance(value, dict):
            validate_primitive_dict(value)
        elif isinstance(value, list):
            validate_primitive_list(value)
        else:
            validate_is_primitive(value)
        
def validate_primitive_list(l: list):
    """ Validate that all base-level elements within a list are primitive values. """
    for value in l:
        if isinstance(value, dict):
            validate_primitive_dict(value)
        elif isinstance(value, list):
            validate_primitive_list(value)
        else:
            validate_is_primitive(value)