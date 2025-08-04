"""
Type Registration Module

This module provides a centralized type registry for managing all serializable types
in the application. The module maintains a stateful `type_registry` object.
"""

from .registration.type_registry import TypeRegistry

# Expose these at the module level
from .registration.create_type_registry import create_type_registry 
from .fields.get_field_name import get_field_name
from ..utilities.validation_error import ValidationError

# Module-level stateful variable - will be populated when create_type_registry() is called
type_registry: TypeRegistry = TypeRegistry.initialize()