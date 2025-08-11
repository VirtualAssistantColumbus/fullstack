from enum import Enum, IntEnum, StrEnum
from typing import Any

from .safe_str import SafeStr

from ...document.document_context import DocumentContext
from ..registration.type_info import TypeInfo
from ...document.document_id import DocumentId
from ..fields.field_path import FieldPath
from .typed_list import TypedList


"""
Default pseudoprimitives and serialization functions.
"""

_pseudo_primitives: list[type] = [
	# Sequences
	TypedList, list, frozenset, set, tuple,
	
	# Strings
	DocumentId, FieldPath,
	
	# Enum types
	StrEnum, IntEnum
]

def _pseudo_primitive_to_bson(obj: Any):
	""" Converts a PseudoPrimitive object to its BSON representation. 
	NOTE: We use the is and in comparators instead of isinstance() because we want to ensure we know *exactly* what types we're serializing (no subclasses allowed). """

	if isinstance(obj, TypedList):
		result = {}
		from ..serialization.obj_to_bson import obj_to_bson
		result = [obj_to_bson(element) for element in obj._elements]
		return result
	elif isinstance(obj, Enum):
		return obj.value
	elif type(obj) in (tuple, set, frozenset, list):
		from ..serialization.obj_to_bson import obj_to_bson
		return [obj_to_bson(item) for item in obj]
	elif type(obj) in (DocumentId, FieldPath, SafeStr):
		return str(obj)
	elif type(obj) is DocumentId:
		return str(obj)
	else:
		raise TypeError(f"Unable to convert invalid pseudo-primitive type {type(obj).__name__} to BSON.")
	
def _bson_to_pseudo_primitive(bson: Any, expected_type_info: TypeInfo, document_context: DocumentContext | None, *, coerce_str_values: bool = False) -> Any:
	""" Deserializes a BSON document into a PseudoPrimitive object. """
	
	if issubclass(expected_type_info.type_, TypedList):
		from ..serialization.bson_to_type_annotation import bson_to_type_annotation
		
		if not isinstance(bson, list):
			raise ValueError(f"Expected a list for TypedList field. Instead received {type(bson).__name__}\n\n[Document Context]\n{document_context}")
		
		allowed_types = expected_type_info.type_.__allowed_types__
		if len(allowed_types) != 1:
			raise ValueError("TypedList must have only one allowable type to be deserializable. Otherwise, we wouldn't know what type each element is.")
		allowed_type = allowed_types[0]
		
		obj_list = []
		for idx, element in enumerate(bson):
			new_document_context = document_context.subidx(idx) if document_context else None
			obj_element = bson_to_type_annotation(element, allowed_type, new_document_context)
			if not isinstance(obj_element, allowed_type):
				raise ValueError(f"Element in list is not of expected type {allowed_type.__name__}. Instead received {type(obj_element).__name__}.\n\n[Document Context]\n{document_context}")
			obj_list.append(obj_element)
		
		return expected_type_info.type_(obj_list)

	elif expected_type_info.type_ in (tuple, set, frozenset, list):
		from ..serialization.bson_to_type_annotation import bson_to_type_annotation
		
		if expected_type_info.sub_type is None:
			raise ValueError("Sequences should have a subtype specified.\n\n[Document Context]\n{document_context}")
		
		obj_list = []
		for idx, element in enumerate(bson): # An error will be raised here if its not actually an iterable type
			new_document_context = document_context.subidx(idx) if document_context else None
			assert isinstance(expected_type_info.sub_type, type)
			obj_element = bson_to_type_annotation(element, expected_type_info.sub_type, new_document_context, coerce_str_values=coerce_str_values)
			obj_list.append(obj_element)
		
		return expected_type_info.type_(obj_list)

	elif expected_type_info.type_ in (DocumentId, FieldPath, SafeStr):
		if not isinstance(bson, str): 
			raise ValueError(f"Expected a str for field of type {expected_type_info.type_.__name__}. Instead received {type(bson).__name__}.\n\n[Document Context]\n{document_context}")
		return expected_type_info.type_(bson)

	elif issubclass(expected_type_info.type_, Enum):
		if isinstance(bson, str) and coerce_str_values:
			if issubclass(expected_type_info.type_, (IntEnum)):
				try:
					bson = int(bson)
				except ValueError:
					raise ValueError(f"Could not convert string '{bson}' to int for Enum field.\n\n[Document Context]\n{document_context}")
			# StrEnum and regular Enum can use the string value directly
		
		try:
			enum = expected_type_info.type_(bson)
		except Exception as e:
			raise ValueError(f"Error deserializing Enum: {e}.\n\n[Document Context]\n{document_context}")
		return enum
	
	else:
		raise ValueError(f"Unable to deserialize invalid pseudo-primitive type {expected_type_info.type_}.\n\n[Document Context]\n{document_context}")