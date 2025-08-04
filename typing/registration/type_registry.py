from dataclasses import dataclass
from typing import Any, Callable, ForwardRef, TYPE_CHECKING
from bidict import bidict

if TYPE_CHECKING:
    from ..bsonable_dataclass.bsonable_dataclass import BsonableDataclass
    from ...document.document_info import listDocumentInfo


class TypeNameDict(bidict[str, type]):
    def add(self, type_: type) -> None:
        """Register a single type by its name."""
        self[type_.__name__] = type_
    def add_list(self, types: list[type]) -> None:
        """Register multiple types by their names."""
        for type_ in types:
            self.add(type_)

@dataclass
class TypeRegistry:
    """ A registry of all types that can be stored and retrieved from MongoDb. """
    document_info_list: 'listDocumentInfo'
    
    # Type lists, useful for isintance, issubclass checks in our routing within obj_to_bson, bson_to_obj
    abstract_bsonable_dataclass_list: list[type['BsonableDataclass']]
    concrete_bsonable_dataclass_dict: list[type['BsonableDataclass']]
    
    pseudo_primitives: list[type]
    pseudo_primitive_to_bson: Callable[[Any], Any]
    bson_to_pseudo_primitive: Callable[..., Any]
    """ Expected function signature: 
    (bson: Any, expected_type_info: TypeInfo, document_context: DocumentContext | None, *, coerce_str_values: bool = False) -> Any """
    
    primitives: list[type]

    type_id_dict: bidict[str, type]
    """ Type dictionary with all serializable types. """
    
    type_name_dict: TypeNameDict
    """ Type dictionary with *all* types, including abstract dataclasses. """

    @classmethod
    def initialize(cls) -> 'TypeRegistry':
        from ...document.document_info import listDocumentInfo
        return TypeRegistry(
            document_info_list=listDocumentInfo(),
            abstract_bsonable_dataclass_list=[],
            concrete_bsonable_dataclass_dict=[],
            pseudo_primitives=[],
            pseudo_primitive_to_bson=None,
            bson_to_pseudo_primitive=None,
            primitives=[],
            type_id_dict=bidict(),
            type_name_dict=TypeNameDict()
        )

    # @property
    # def bsonable_dataclasses(self) -> tuple[type[BsonableDataclass], ...]:
    #     """ Returns a list of all registered BsonableDataclasses. """
    #     return tuple(self.abstract_bsonable_dataclass_list) + tuple(self.concrete_bsonable_dataclass_dict.values())

    # def type_id_to_cls(self, type_id: str) -> type[BsonableDataclass]:
    #     return self.concrete_bsonable_dataclass_dict[type_id]

    def type_to_type_id(self, type: type) -> str | None:
        """ Return the type id for the type. """
        return self.type_id_dict.inverse.get(type)

    def lookup_type_by_type_id(self, type_id: str) -> type['BsonableDataclass'] | None:
        """ Returns None if no Bsonable found with matching type id. """
        return self.type_id_dict.get(type_id)
    
    def serialize(self, obj: Any):
        """ Wraps obj_to_bson for easy access. """
        from ..serialization.obj_to_bson import obj_to_bson
        return obj_to_bson(obj)
    
    def is_primitive_cls(self, cls: type) -> bool:
        """Returns True if the class is a primitive type."""
        return cls in self.primitives # Primitive should exactly match a primitive type, not be a subclass
        
    def is_pseudo_primitive_cls(self, cls: type) -> bool:
        """Returns True if the class is a pseudo-primitive type."""
        return issubclass(cls, tuple(self.pseudo_primitives))
    
    def is_pseudo_primitve_instance(self, obj: Any):
        return isinstance(obj, tuple(self.pseudo_primitives))
    
    def is_primitive_instance(self, obj: Any):
        return isinstance(obj, tuple(self.primitives))

    def resolve_forward_ref(self, forward_ref: str | ForwardRef) -> type:
        """
        Resolves a ForwardRef or string type name to its actual type using the registered types in type_dict.
        
        Args:
            forward_ref: The ForwardRef or string type name to resolve
            
        Returns:
            The resolved type
            
        Raises:
            ValueError: If the type cannot be resolved using registered types
        """
        # Get the type name from either a ForwardRef or string
        if isinstance(forward_ref, str):
            type_name = forward_ref
        elif isinstance(forward_ref, ForwardRef):
            type_name = forward_ref.__forward_arg__
        else:
            raise ValueError(f"Expected ForwardRef or string, got {type(forward_ref)}")
            
        # Look up type name in cached dictionary
        if type_name in self.type_name_dict:
            return self.type_name_dict[type_name]
        
        print(self.type_name_dict)
                
        raise ValueError(f"Could not resolve type '{type_name}'. Type not found in registry.")