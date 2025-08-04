from typing import Any

from .field_schema import FieldSchema


def get_field_name(bsonable_field: Any) -> str:
    """ Get the name of the bsonable field. """
    if not isinstance(bsonable_field, FieldSchema):
        raise
    return bsonable_field.field_name