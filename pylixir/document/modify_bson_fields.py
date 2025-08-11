from typing import Any


def rename_field(bson: Any, old_field_name: str, new_field_name, *, preserve_old_field: bool = False):
    """ Renames a field in the bson. """

    if old_field_name in bson:
        bson[new_field_name] = bson[old_field_name]
        if not preserve_old_field:
            del bson[old_field_name]

def delete_field(bson: Any, field_name: str):
    """ Deletes the field, if it exists. """
    if field_name in bson:
        del bson[field_name]

def add_field(bson: Any, field_name: str, field_value: Any, *, overwrite: bool = False):
    """ field_value must be *bson* not a Python object. """
    if overwrite or not field_name in bson:
        bson[field_name] = field_value