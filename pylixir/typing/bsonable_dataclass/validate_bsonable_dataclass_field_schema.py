from typing import ForwardRef

from .bsonable_dataclass import BsonableDataclass
from ...utilities.logger import logger
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..registration.type_registry import TypeNameDict


def validate_bsonable_dataclass_field_schema(type_name_dict: 'TypeNameDict', concrete_bsonable_dataclasses: list[type[BsonableDataclass]]):
    """ Validates that all BsonableDataclasses fields are annotated to store a serializable type. """
    for bsonable_dataclass in concrete_bsonable_dataclasses:
        for field_name, field_schema in bsonable_dataclass.__bsonable_fields__.items(): 
            field_type = field_schema.type_expectation.type_info.type_
            
            # Evaluate any forward refs and update the field schema in __bsonable_fields__
            if isinstance(field_type, (ForwardRef, str)):
                # This doesn't yet handle nullable forward refs
                evaluated_type = type_name_dict[field_type]
                field_schema.type_expectation.type_info.type_ = evaluated_type
                logger.debug(f"Successfully evaluated ForwardRef {bsonable_dataclass.__name__}.{field_name} to type {evaluated_type.__name__} and updated field schema.")
                continue
            
            # If it's an actual type, just check to make sure it's actually a bsonable type
            if not issubclass(field_type, tuple(type_name_dict.values())):
                raise ValueError(f"Bsonable dataclass '{bsonable_dataclass.__name__}' contains a field '{field_name}' which stores a non-serializable type {field_type.__name__}.")