from dataclasses import dataclass
from typing import Any, Callable

from ...utilities.undefined import Undefined, UNDEFINED
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .field_pointer import DocumentFieldPointer


@dataclass
class _SchemaConfig:
    """ Do not instantiate this directly. Use BsonableField() instead. """
    default_value: Any | Undefined
    default_factory: Callable[[], Any] | None
    kw_only: bool
    """ Specify whether we should allow this field to be edited by an externally specified field pointer. """
    validation_func: Callable[[Any], None] | None

    def has_default(self) -> bool:
        if self.default_value is not UNDEFINED or self.default_factory is not None:
            return True
        return False

    def get_default(self) -> Any:
        if self.default_value is not UNDEFINED:
            return self.default_value
        elif self.default_factory is not None:
            return self.default_factory()
        else:
            raise ValueError(f"No default value set.")

@dataclass
class _DocumentSchemaConfig(_SchemaConfig):
    """ Extends _SchemaConfig to allow a document validation function which will be used when updating the individual fields and updating the full document. """
    allow_independent_update: bool
    document_update_validation_func: Callable[['DocumentFieldPointer', Any], None] | None
    """ The update validation function will have access to a pointer to itself. """
    document_insertion_validation_func: Callable[[Any, Any], None] | None
    """ The inseration validation func will have access to the entire document we are attempting to insert. """

    @classmethod
    def from_schema_config(cls, schema_config: _SchemaConfig) -> '_DocumentSchemaConfig':
        """ Creates a new _DocumentSchemaConfig from an existing _SchemaConfig, preserving all the existing config values but adding document_validation_func=None """
        return _DocumentSchemaConfig(
            default_value=schema_config.default_value,
            default_factory=schema_config.default_factory,
            kw_only=schema_config.kw_only,
            validation_func=schema_config.validation_func,
            allow_independent_update=False, # Default to not allow independent editing
            document_update_validation_func=None, # Default to no document update field validation
            document_insertion_validation_func=None # Default to no document insertion field validation
        )

def SchemaConfig(
        # Note that for a field specifier, the following parameters are recognized by dataclass_transform as having special properties:
        #   - default
        #   - default_factory
        #   - kw_only
        *,
        default: Any | Undefined = UNDEFINED,
        default_factory: Callable[[], Any] | None = None,
        kw_only: bool = False,
        validation_func: Callable[[Any], None] | None = None
    ) -> Any:
    """ Use this to add configurations to BsonableDataclass fields.
    
    Factory method for generating FieldConfig, with defaults.
    The generated FieldConfig will be consumed by BsonableDataclassMeta, stashed into FieldSchema.field_config, and then stored into the class field as well as registered into cls.__bsonable_fields__
    
    Declare the return type as 'Any' so that the static type-checker doesn't complain. (Type checkers expect class fields to be the same type as instance fields.) """
    
    if default is not UNDEFINED and default_factory is not None:
        raise ValueError("Cannot specify both default_value and default_factory")

    return _SchemaConfig(
        default_value=default,
        default_factory=default_factory,
        kw_only=kw_only,
        validation_func=validation_func
    )

def DocumentSchemaConfig(
        # Note that for a field specifier, the following parameters are recognized by dataclass_transform as having special properties:
        #   - default
        #   - default_factory
        #   - kw_only
        *,
        default: Any | Undefined = UNDEFINED,
        default_factory: Callable[[], Any] | None = None,
        kw_only: bool = False,
        
        # Specify whether this field can be modified via API by a pointer
        allow_independent_update: bool = False,
        validation_func: Callable[[Any], None] | None = None,
        
        # This should accept self + the new value
        document_update_validation_func: Callable[['DocumentFieldPointer', Any], None] | None = None,
        document_insert_validation_func: Callable[[Any, Any], None] | None = None
    ) -> Any:
    """ Use this to add configurations to Document fields.
    
    Factory method for generating DocumentFieldConfig, with defaults.
    Extends SchemaConfig with document validation functionality.
    """
    
    if default is not UNDEFINED and default_factory is not None:
        raise ValueError("Cannot specify both default_value and default_factory")

    return _DocumentSchemaConfig(
        default_value=default,
        default_factory=default_factory,
        kw_only=kw_only,
        allow_independent_update=allow_independent_update,
        validation_func=validation_func,
        document_update_validation_func=document_update_validation_func,
        document_insertion_validation_func=document_insert_validation_func
    )