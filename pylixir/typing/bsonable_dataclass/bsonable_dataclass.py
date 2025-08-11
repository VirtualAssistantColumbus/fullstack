from abc import ABC
from typing import Any, ClassVar, Self

from .bsonable_dataclass_meta import SPECIAL_INSTANCE_FIELDS, BsonableDataclassMeta
from ..fields.field_schema import FieldSchema
from ...utilities.special_values import ABSTRACT
from ..serialization.vars import __type_id__, get_type_id
from ...utilities.logger import logger

from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from ...document.document_context import DocumentContext


class BsonableDataclass(ABC, metaclass=BsonableDataclassMeta):
	""" All mappable dataclasses must specify a __type_id__. """
	__bsonable_fields__: ClassVar[dict[str, FieldSchema]] # Special field that stores a dictionary mapping field names -> field schemas
	__type_id__: ClassVar[str] = ABSTRACT

	def __str__(self) -> str:
		output = f"{type(self).__name__}(\n"
		for field_name, field_value in self.__dict__.items():
			if field_name in SPECIAL_INSTANCE_FIELDS:
				continue
			output += f"\t{field_name}={repr(field_value)},\n"
		output += ")"
		return output

	def __post_init__(self) -> None:
		""" By default, post init does nothing. """
		return

	@classmethod
	def inspect_type_id(cls, bson: Any, document_context: 'DocumentContext | None') -> type['BsonableDataclass'] | None:
		""" Inspect the bson for a __type_id__. If the __type_id__ is a valid subclass of this cls, returns the type. Otherwise, returns None. 
		
		Bsonable classes should start their from_bson() methods with the following code:
		
		valid_subtype = cls.inspect_type_id(bson, document_context)
		if valid_subtype:
			if not issubclass(valid_sub_type, cls): raise # type cast
			return valid_subtype.from_bson(bson, document_context)

		"""
		from .. import type_registry

		type_id = get_type_id(bson, document_context)
		if type_id:
			bson_asserted_type = type_registry.lookup_type_by_type_id(type_id)
			if bson_asserted_type:
				if bson_asserted_type is cls:
					return None
				elif issubclass(bson_asserted_type, cls):
					return bson_asserted_type
				else:
					logger.info(f"Warning: Bson asserted a __type_id__ that is not a subclass of expected type '{cls.__name__}'\n{document_context}")
			else:
				logger.info(f"Warning: Bson asserted an unrecognized __type_id__ '{type_id}'.\n{document_context}")

	def to_bson(self) -> dict[str, Any]:
		from ..serialization.obj_to_bson import obj_to_bson
		
		# Raise error for abstract classes
		if type(self).__type_id__ == ABSTRACT:
			raise ValueError(f"Error serializing object of type '{type(self).__name__}'. Abstract classes cannot be serialized.")
		
		# Convert to document
		output = { __type_id__: type(self).__type_id__ } # Initialize the dict with __type_id__

		for field_name, field_schema in type(self).__bsonable_fields__.items():
			value = getattr(self, field_name)
			output[field_name] = obj_to_bson(value)

		# Allow extra fields
		# Also serialize any additional fields that may be stored within the object beyond what is annotated
		# This helps with forward-compatibility when implementing new features
		for key, value in self.__dict__.items():
			# Skip over all keys we've already looked at
			if key in type(self).__bsonable_fields__.keys():
				continue

			# Skip all special fields
			if key.startswith("__"): # If you modify this, make sure you explicitly skip __type_id__ so that we don't override the value from super()
				continue

			# Store loose fields into the result
			output[key] = obj_to_bson(value)

		return output

	@classmethod
	def from_bson(cls, bson: Any, document_context: 'DocumentContext | None', *, coerce_str_values: bool = False) -> Self:
		""" Define how this BsonableDataclass should be instantiated from a bson document that matches this version. """
		""" If an annotated field has a default value, it will be set to the default if not in document. """
		from ..serialization.bson_to_type_expectation import bson_to_type_expectation

		# See if there is a valid subtype, if so, deserialize it into that instead of this cls.
		valid_subtype = cls.inspect_type_id(bson, document_context)
		if valid_subtype:
			if not issubclass(valid_subtype, cls):
				raise
			return valid_subtype.from_bson(bson, document_context)

		# Raise an error when deserializing abstract classes. (Subclasses of abstract classes would have asserted a valid_type_id above and not reached this step.)
		if cls.__type_id__ == ABSTRACT:
			raise ValueError(f"Error deserializing bson into abstract class of type {type(cls).__name__}. In order to deserialize an abstract class, the bson itself must assert a valid subtype of the abstract class.\n{document_context}")
		
		# Deserialize the bson into this type
		obj_dict = {}
		
		# Look for all expected fields
		for expected_field_name, expected_field_schema in cls.__bsonable_fields__.items():
			
			# Look for this field in the following order:
			# 1. If the field name exists in the document, use that.
			# 2. If the field name does not exist in the document, look for a legacy field name and use that if found.
			# 3. If there is no legacy field name, use a default value, if set.
			# 4. If all else fails, raise an Exception.
			legacy_field_name = expected_field_name + "__legacy__"
			# If the document has the field, convert it into an object and stash the obj into the obj_dict
			if expected_field_name in bson:
				document_attr_value = bson[expected_field_name]
				new_document_context = document_context.subpath(expected_field_name) if document_context else None
				attr_obj = bson_to_type_expectation(document_attr_value, expected_field_schema.type_expectation, new_document_context, coerce_str_values=coerce_str_values)
				obj_dict[expected_field_name] = attr_obj
			
			# Look for a legacy field
			elif legacy_field_name in bson:
				document_attr_value = bson[expected_field_name]
				logger.info(f"Using legacy field {legacy_field_name} with value {document_attr_value} for {expected_field_name}.\n\n{document_context}")
				new_document_context = document_context.subpath(legacy_field_name) if document_context else None
				attr_obj = bson_to_type_expectation(document_attr_value, expected_field_schema.type_expectation, new_document_context, coerce_str_values=coerce_str_values) # Legacy field still must conform to the original type expectation
				obj_dict[expected_field_name] = attr_obj
				
			# If the field has a default value, set it to that
			elif expected_field_schema.schema_config.has_default():
				field_default_value = expected_field_schema.schema_config.get_default()
				logger.warning(f"Using default value of {field_default_value} for {expected_field_name}.\n\n{document_context}")
				obj_dict[expected_field_name] = field_default_value # NOTE: It's at this point that the Mongoable object will be assigned a random _id if the _id is not in the document
			
			# Otherwise, raise an error
			else:
				raise ValueError(f"Error converting document to object of type {cls.__name__}. Document missing a value for field {expected_field_name}.\n\n{document_context}")
				
		# Remove __type_id__ from the bson
		if __type_id__ in bson:
			del bson[__type_id__]
		
		# Allow extra fields
		# Also deserialize and store fields beyond what is expected within the type.
		# This helps with forward-compatibility when it comes to implementing new features that rely on additional fields.
		for key, value in bson.items():
			# Skip over all keys we've already looked at
			if key in cls.__bsonable_fields__.keys():
				continue

			# Store loose fields into the object
			obj_dict[key] = value

		return cls(**obj_dict)

	# def get_value_at_field_path(self, field_path: 'FieldPath') -> Any:
	# 	""" Returns the value stored at the field path. """
	# 	if field_path.get_root_type_id() != type(self).__type_id__:
	# 		raise ValueError("Field path is inconsistent with this BsonableDataclass.")
		
	# 	# Drill down through the nested fields until we find the immediate parent of the final field. (This drills down through the *instance* fields.)
	# 	field_names = field_path.get_parts()
	# 	immediate_parent = self
	# 	for field_name in field_names[:-1]:
	# 		if not hasattr(immediate_parent, field_name):
	# 			raise ValueError(f"{type(immediate_parent).__name__} does not have a field named {field_name}.")
			
	# 		# Validate that the field is modifiable by API before drilling into it
	# 		field_info = expect_type(getattr(type(immediate_parent), field_name), FieldSchema)
	# 		if not field_info.schema_config.allow_edit_by_pointer:
	# 			raise ValueError(f"Field '{field_name}' within class '{type(immediate_parent).__name__}' is not allowed to be modified via API. Attempted field access: {self}.")
			
	# 		immediate_parent = getattr(immediate_parent, field_name)
		
	# 	# Handle the last field (the attribute that we actually want to update)
	# 	final_field_name = field_names[-1]
	# 	final_field_info = getattr(type(immediate_parent), final_field_name)
	# 	if not isinstance(final_field_info, FieldSchema):
	# 		raise ValueError(f"Field '{final_field_name}' is not a FieldSchema. Attempted field access: {self}.")
		
	# 	# Validate that this field is allowed to be set by the api
	# 	if not final_field_info.schema_config.allow_edit_by_pointer:
	# 		raise ValueError(f"Field '{final_field_name}' is not allowed to be modified via API. Attempted field access: {self}.")

	# 	# Get the attribute on the immediate parent
	# 	field_value = getattr(immediate_parent, final_field_name)

	# 	return field_value