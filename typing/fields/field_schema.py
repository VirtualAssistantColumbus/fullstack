from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .schema_config import _DocumentSchemaConfig, _SchemaConfig
if TYPE_CHECKING:
    from ..bsonable_dataclass.bsonable_dataclass import BsonableDataclass
    from ..registration.type_expectation import TypeExpectation


class FieldSchema:
    """ Stores the schema for the field, i.e. its relationship structure. """
    def __init__(self, 
                 field_name: str,
                 containing_cls: type[BsonableDataclass],
                 type_expectation: TypeExpectation,
                 configuration: _SchemaConfig | _DocumentSchemaConfig  # This may store either a _SchemaConfig OR a _DocumentFieldCon
                ) -> None:
        self.field_name = field_name
        self.containing_cls = containing_cls
        self.type_expectation = type_expectation
        self.schema_config = configuration

    def validate_field_value(self, field_value: Any) -> None:
        """ Validates the field value first against the type expectation, then against the validation func, if any. 
        These should raise a ValidationError with a client-shareable error mesage. """
        
        # Validate against type expectation
        self.type_expectation.validate(field_value, None)
        
        # Validate against validation func
        if self.schema_config.validation_func is not None:
            validation_func = self.schema_config.validation_func
            
            # Check if it's a bound method (instance method)
            if isinstance(validation_func, classmethod):
                # Get the underlying function and call it with the containing class
                actual_func = validation_func.__get__(None, self.containing_cls).__func__
                actual_func(self.containing_cls, field_value)
            else:
                # Static method or regular function
                validation_func(field_value)