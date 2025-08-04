from typing import Any, TypeVar

from flask_login import current_user

from ..typing.bsonable_dataclass.bsonable_dataclass import BsonableDataclass
from .document import Document
from .document_id import PUBLIC
from ..utilities.result import UpdateFieldResult
from ..typing.fields.field_pointer import DocumentFieldPointer
from ..typing.fields.schema_config import _DocumentSchemaConfig
from ..typing.registration.get_type_expectation_from_type_annotation import get_type_expectation_from_type_annotation
from ..utilities.undefined import UNDEFINED, Undefined
from ..typing import type_registry


V = TypeVar('V', bound=BsonableDataclass)

def validate_document_ownership(document: Document):
    # Enforce that the user owners this document
    document_owner = document.get_owner()
    if not document_owner == PUBLIC:
        # First check we have a logged in user
        if not current_user.is_authenticated:
            raise RuntimeError(f"This document requires authentication to be accessed.")
        
        # Ensure the logged in user's id matches the document owner's id
        logged_in_user_id = current_user.get_id()
        if logged_in_user_id != document_owner:
            raise ValueError(f"Error: This pointer points to a field within a document that doesn't belong to the logged in user '{logged_in_user_id}'. Cannot access.")

def update_pointer_value(pointer: DocumentFieldPointer, new_value: Any) -> UpdateFieldResult:
    """ UserContext.update_pointer_value() ensures that the logged in user can only update documents that belong to them. """
    # Always validate pointer ownership and access controls
    document_cls = pointer.document_cls()
    document = document_cls.db_require_one_by_id(pointer.document_id)

    # VERY IMPORTANT
    validate_document_ownership(document)

    document.db_update_self_field(pointer.field_path, new_value)
    return UpdateFieldResult(True, pointer.field_path)  

def deference_pointer(pointer: DocumentFieldPointer, expected_type: type[V] | Undefined = UNDEFINED) -> V:
    """ Dereference the pointer value. """
    # Get the document cls
    document_cls = type_registry.document_info_list.type_id_to_cls(pointer.field_path.get_root_type_id())

    # Get the document from the database    
    document = document_cls.db_find_one({ "_id": pointer.document_id})
    if not document:
        raise ValueError(f"Can't find document of type '{document_cls.__type_id__}' with _id '{pointer.document_id}'")
    
    # VERY IMPORTANT
    # Validates whether this is being accessed by a logged in user
    validate_document_ownership(document)
    
    # Validate we can access this field
    field_schema = pointer.field_path.field_schema()
    if not isinstance(field_schema.schema_config, _DocumentSchemaConfig):
        raise ValueError(f"Field '{field_schema.field_name}' is not configured with DocumentFieldSchema. Attempted field access: {pointer}")
    if not field_schema.schema_config.allow_independent_update:
        raise ValueError(f"The field '{field_schema.field_name}' within class '{pointer.document_cls().__name__}' is not independently updateable.")

    # Return the value
    field_value = pointer.field_path.navigate_into(document)
    
    # Type check if expected_type is provided
    if not isinstance(expected_type, Undefined):
        # Generate a TypeExpectation from the annotation
        type_expectation = get_type_expectation_from_type_annotation(expected_type)
        type_expectation.validate(field_value, None)
        
    return field_value