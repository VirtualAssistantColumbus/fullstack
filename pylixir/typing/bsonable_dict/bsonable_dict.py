from typing import ClassVar, TypeVar, Generic, Dict, Any, Self, Mapping, Iterator
from collections.abc import MutableMapping
from abc import ABCMeta

from ...document.document_context import DocumentContext
from ..serialization.bson_to_primitive import str_to_primitive
from ..serialization.primitive_to_bson import primitive_to_str
from ...utilities.special_values import AUTO
from ..serialization.vars import __type_id__
from ..registration.get_type_expectation_from_type_annotation import get_type_expectation_from_type_annotation
from ..registration.type_info import TypeInfo
from ..fields.schema_config import _SchemaConfig, SchemaConfig
from ..fields.field_schema import FieldSchema
from ...utilities.undefined import UNDEFINED, Undefined

def pseudo_primitive_to_str(obj: Any) -> str:
	""" Converts a PseudoPrimitive object to its string representation by first converting to BSON. """
	from .. import type_registry
	from ..serialization.primitive_to_bson import primitive_to_str
	bson = type_registry.pseudo_primitive_to_bson(obj)
	return primitive_to_str(bson)

__key__ = "__key__"
__value__ = "__value__"

K = TypeVar('K')
V = TypeVar('V')

class BsonableDictMeta(ABCMeta):
	"""Metaclass for BsonableDict that handles type registration and schema generation.
	
	This metaclass performs several key functions:
	1. Assigns AUTO type IDs if specified
	2. Ensures __key__ and __value__ are properly specified via annotations
	3. Converts __value__ annotation into a FieldSchema for validating dictionary values
	4. Handles SchemaConfig and DocumentSchemaConfig for value configuration
	"""
	def __new__(cls, name, bases, dct):
		# Create the new class
		new_cls = super().__new__(cls, name, bases, dct)
		
		# Skip validation for the base BsonableDict class
		if name == 'BsonableDict':
			return new_cls
		
		# Assign AUTO type ids
		type_id = getattr(new_cls, __type_id__, None)
		if type_id == AUTO:
			setattr(new_cls, __type_id__, name)
		
		# Get annotations
		annotations = dct.get('__annotations__', {})
		
		# Handle key type
		if __key__ not in annotations:
			raise TypeError(f"BsonableDict subclass '{name}' must specify __key__ annotation")
		key_type = annotations[__key__]
		setattr(new_cls, __key__, key_type)
		
		# Handle value type and schema
		if __value__ not in annotations:
			raise TypeError(f"BsonableDict subclass '{name}' must specify __value__ annotation")
		
		value_type_annotation = annotations[__value__]
		type_expectation = get_type_expectation_from_type_annotation(value_type_annotation)
		
		# Get schema config (default to SchemaConfig if none specified)
		if not hasattr(new_cls, __value__):
			value_schema_config = SchemaConfig()
		else:
			value_schema_config = getattr(new_cls, __value__)
			# If we assign a non schema config value, we convert it to the default value. Not that a default value is currently used.
			if not isinstance(value_schema_config, _SchemaConfig):
				value_schema_config = SchemaConfig(default=value_schema_config)
			
		# Generate FieldSchema for value type
		value_schema = FieldSchema(
			field_name='value',  # Generic field name since this applies to all values
			containing_cls=new_cls, # type: ignore
			type_expectation=type_expectation,
			configuration=value_schema_config
		)
		
		# Store both the type and schema
		setattr(new_cls, __value__, value_schema)
		
		return new_cls

class BsonableDict(Generic[K, V], MutableMapping[K, V], metaclass=BsonableDictMeta):
	"""A dictionary with strongly typed keys and values that can be serialized to BSON.
	
	Keys must be primitives or pseudoprimitives.
	Values can be primitives, pseudoprimitives, or BsonableDataclasses.

	The class uses a FieldSchema (stored in __value_type__ after metaclass processing) to validate 
	all values stored in the dictionary, ensuring type safety and proper serialization behavior.

	To define a BsonableDict:
	```python
	class MyDict(BsonableDict[str, int]):
		__type_id__ = AUTO  # Optional, defaults to class name
		__key__: str
		__value__: MyClass = SchemaConfig()
	```

	Class Attributes:
		__type_id__: Type identifier for BSON serialization
		__key__: Type of the dictionary keys (must be primitive or pseudoprimitive)
		__value_type__: Initially the type annotation, converted to FieldSchema by metaclass
		__limit_keys__: Optional list of allowed keys
		default_dict(): Optional, generates default dictionary for initialization

	Args:
		initial_elements: Optional dictionary to initialize with
	"""
	__type_id__: ClassVar[str] # type ids for bsonable dicts are really usef for anything at the moment, but I have it here for consistency so that we can register all BsonableDicts with a type_id into the sharedd type_dict
	
	# These are annotated as the types they will be after the metaclass operates on the class
	__key__: ClassVar[type]
	__value__: ClassVar[FieldSchema]
	
	__limit_keys__: list[K] | None = None  # Use this if you want to limit the keys to specific set of values
	
	@classmethod
	def default_dict(cls) -> dict[K, V]:
		""" Override this provide a default. """
		return {}
	
	@classmethod
	def default_value(cls) -> V | Undefined:
		""" Override this if you want to return a default value when accessing a key that is not defined. """
		return UNDEFINED
	
	def __init__(self, initial_elements: dict[K, V] | None = None):
		# Initialize to the default dict or to an empty dict.
		if initial_elements:
			self._elements = initial_elements
		else:
			self._elements = self.default_dict()
		
		# Validate only after we've set up the default (for example, some intermerdiary states may not be valid, but the final state could be)
		self.__validate_dict__()
	
	def __validate_dict__(self) -> None:
		"""Override this method to perform validation when the dict is modified."""
		pass
		
	def __check_types__(self, key: K, value: V):
		"""Validate both key and value types."""
		if not isinstance(key, self.__key__):
			raise TypeError(f"Invalid key type {type(key).__name__}. Expected {self.__key__.__name__}")
		
		# TODO: Improve this. Value expectation should be instantiated and stashed when the class is created
		value_expectation = self.__value__.type_expectation
		value_expectation.validate(value, None)
		if self.__limit_keys__ is not None and key not in self.__limit_keys__:
			raise KeyError(f"Key '{key}' is not allowed. Allowed keys are: {self.__limit_keys__}")
	
	def __getitem__(self, key: K) -> V:
		if self.__limit_keys__ is not None and key not in self.__limit_keys__:
			raise KeyError(f"Key '{key}' is not allowed. Allowed keys are: {self.__limit_keys__}")
		
		if key in self._elements:
			return self._elements[key]
		else:
			default_value = type(self).default_value()
			if default_value is not UNDEFINED:
				value_expectation = self.__value__.type_expectation
				value_expectation.validate(default_value, None)
				return default_value # type: ignore
			else:
				raise KeyError(f"Key '{key}' not found in {type(self).__name__} and no default value is defined")
	
	def __contains__(self, key: object) -> bool:
		return key in self._elements

	def get(self, key: K, default: V | None = None) -> V | None:
		return self._elements.get(key, default)

	def __setitem__(self, key: K, value: V):
		self.__check_types__(key, value)
		self._elements[key] = value
		self.__validate_dict__()
		
	def __delitem__(self, key: K):
		del self._elements[key]
		self.__validate_dict__()
		
	def __iter__(self) -> Iterator[K]:
		return iter(self._elements)
		
	def __len__(self) -> int:
		return len(self._elements)
		
	def __str__(self) -> str:
		return str(self._elements)

	def update(self, other: Mapping[K, V] | Dict[K, V]) -> None:
		"""Update the dictionary with elements from another mapping or dictionary, enforcing types."""
		for key, value in other.items():
			self[key] = value  # This will call __setitem__ which enforces types
	
	@classmethod
	def from_bson(cls, bson: Dict[Any, Any], document_context: DocumentContext | None, *, coerce_str_values: bool = False) -> Self:
		"""Convert a BSON dictionary into a BsonableDict instance."""
		from ..serialization.bson_to_type_annotation import bson_to_type_annotation
		from .. import type_registry

		if not isinstance(bson, dict):
			raise ValueError(f"Expected a dict for BsonableDict field. Instead received {type(bson).__name__}\n\n[Document Context]\n{document_context}")
		
		# Remove metadata fields (not currently used in deserialization)
		bson = bson.copy()
		bson.pop(__type_id__, None)
		bson.pop(__key__, None)
		bson.pop(__value__, None)
		
		obj_dict = {}
		for k, v in bson.items():
			
			# TODO: Update this and FieldPath to be able to track document context within a bsonable dict
			if type_registry.is_pseudo_primitive_cls(cls.__key__):
				obj_key = type_registry.bson_to_pseudo_primitive(k, TypeInfo(cls.__key__, None), document_context, coerce_str_values=True)
			elif type_registry.is_primitive_cls(cls.__key__):
				obj_key = str_to_primitive(k, TypeInfo(cls.__key__, None), document_context)
			else:
				raise TypeError(f"Keys in BsonableDicts must be configued as primitives or pseudoprimitives. Instead, we got the following type for a key: '{cls.__key__.__name__}'.")
			
			obj_value = bson_to_type_annotation(v, cls.__value__.type_expectation.type_info.type_, document_context, coerce_str_values=coerce_str_values)
			
			if not isinstance(obj_key, cls.__key__):
				raise ValueError(f"Key in dict is not of expected type {cls.__key__.__name__}. Instead received {type(obj_key).__name__}.\n\n[Document Context]\n{document_context}")
			if not isinstance(obj_value, cls.__value__.type_expectation.type_info.type_):
				raise ValueError(f"Value in dict is not of expected type {cls.__value__.type_expectation.type_info.type_.__name__}. Instead received {type(obj_value).__name__}.\n\n[Document Context]\n{document_context}")
			
			obj_dict[obj_key] = obj_value
		
		return cls(obj_dict)

	def to_bson(self) -> Dict[Any, Any]:
		"""Convert this BsonableDict instance to a BSON-compatible dictionary."""
		from ..serialization.obj_to_bson import obj_to_bson
		from .. import type_registry

		bson_dict = {
			# Add metadata fields for documentation purposes (not currently used in deserialization)
			__type_id__: self.__type_id__,
			__key__: self.__key__.__name__,
			__value__: self.__value__.type_expectation.type_info.type_.__name__
		}
		
		for key, value in self._elements.items():
			# Coerce the key into a str
			if type_registry.is_pseudo_primitve_instance(key):
				bson_key = pseudo_primitive_to_str(key)
			elif type_registry.is_primitive_instance(key):
				bson_key = primitive_to_str(key)
			else:
				raise TypeError(f"Keys in BsonableDicts must be primitives or pseudoprimitives. Instead, we got the following type for a key: '{type(key).__name__}'.")
			
			# Serialize the value normally
			bson_value = obj_to_bson(value)
			bson_dict[bson_key] = bson_value
			
		return bson_dict