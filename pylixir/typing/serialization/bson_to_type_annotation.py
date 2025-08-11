from types import UnionType
from typing import Any

from .vars import __type_id__
from ...document.document_context import DocumentContext
from ..registration.get_type_expectation_from_type_annotation import get_type_expectation_from_type_annotation


# Document to obj
def bson_to_type_annotation(bson: Any, type_annotation: type | UnionType, document_context: DocumentContext | None, *, coerce_str_values: bool = False, resolve_forward_refs: bool = False):
	""" Deserializes a Bson document into a Python object. 
	
	Uses the object's type annotations to interpret the Mongo document.
	
	NOTE: MongoableMeta adds an _id annotation to Mongoable classes so that the _id will be loaded into Mongoable python objects. """
	
	# Determine what type we expect from the bson. We must be able to coerce the document into this type.
	annotated_type_expectation = get_type_expectation_from_type_annotation(type_annotation, resolve_forward_refs=resolve_forward_refs)
	
	# # Determine whether the bson asserts any type information.
	# (bson, bson_type_id, bson_asserted_type_info) = get_document_asserted_type_info(bson, document_context)
	
	# Determine which type we will try to deserialize this bson into. (For example, the bson could assert a subclasses of the annotated type expectation.)
	# deserialization_type_info = determine_deserialization_type(annotated_type_expectation.type_info, bson_asserted_type_info, document_context)
	
	# Always attempt to deserialize into the annotated type info
	from .bson_to_type_expectation import bson_to_type_expectation
	server_obj = bson_to_type_expectation(bson, annotated_type_expectation, document_context, coerce_str_values=coerce_str_values)
	
	return server_obj