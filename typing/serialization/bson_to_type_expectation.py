from typing import Any, ForwardRef

from ..bsonable_dataclass.bsonable_dataclass import BsonableDataclass
from ..bsonable_dict.bsonable_dict import BsonableDict
from .bson_to_primitive import bson_to_primitive
from .. import type_registry
from ...document.document_context import DocumentContext
from ..registration.type_expectation import TypeExpectation


def bson_to_type_expectation(bson: Any, type_expectation: TypeExpectation, document_context: DocumentContext | None, *, coerce_str_values: bool = False):
	""" Deserializes a Bson document into the specified type info. """
	
	# Handle valid null cases
	if bson is None:
		if type_expectation.is_nullable:
			return None
		else:
			raise ValueError(f"Received None for type expectation {type_expectation.type_info} which is not nullable.\n{document_context}")

	### Once we have narrowed down to a single expected type, parse the value into this type. ###
	# Handle types from specific (complex) to general (simple)
	if type_expectation.type_info.type_ is type:
		if type_expectation.type_info.sub_type:
			# The annotated type is the first argument
			annotated_type = type_expectation.type_info.sub_type
			assert not isinstance(annotated_type, ForwardRef)
			# Now you can use this annotated_type as needed
			# For example, you might want to return it directly:
			
			# BsonableDataclasses, which will be annotated type[BsonableDataclass].
			
			# Deserialize by type id
			assert isinstance(bson, str)
			assert bson.startswith("type_id=")
			type_id = bson.removeprefix("type_id=")
			this_type = type_registry.lookup_type_by_type_id(type_id)
			if not this_type:
				raise
			if not issubclass(this_type, annotated_type):
				raise 
			return this_type
		else:
			raise ValueError(f"TYPE annotation without arguments in type expectation.\n{document_context}")		

	elif issubclass(type_expectation.type_info.type_, BsonableDataclass):
		return type_expectation.type_info.type_.from_bson(bson, document_context, coerce_str_values=coerce_str_values)
	
	elif issubclass(type_expectation.type_info.type_, BsonableDict):
		return type_expectation.type_info.type_.from_bson(bson, document_context, coerce_str_values=coerce_str_values)
	
	# First try to catch primitives based on an exact type match. This should not allow for inheritance, and should be checked before we check pseudoprimitives, as some pseudoprimitives may inherit from a primitive.
	elif type_expectation.type_info.type_ in type_registry.primitives:
		return bson_to_primitive(bson, type_expectation.type_info, document_context, coerce_str_values=coerce_str_values)
	
	elif issubclass(type_expectation.type_info.type_, tuple(type_registry.pseudo_primitives)):
		return type_registry.bson_to_pseudo_primitive(bson, type_expectation.type_info, document_context, coerce_str_values=coerce_str_values)

	else:
		raise ValueError(f"Unable to deserialize unregistered expected type {type_expectation.type_info.type_}.\n{document_context}")