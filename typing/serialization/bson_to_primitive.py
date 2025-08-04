from datetime import datetime
from typing import Any

from ...document.document_context import DocumentContext
from ..registration.type_info import TypeInfo


def bson_to_primitive(bson: Any, expected_type_info: TypeInfo, document_context: DocumentContext | None, *, coerce_str_values: bool = False) -> Any:
	""" Converts a BSON document to a primitive type based on the expected type information. """
	
	# If coerce_str_values is set to True, attempt to coerce the value into the expected type info
	# This is typically used if we're processing data from html form elements, which always send their values as strings
	if coerce_str_values and isinstance(bson, str):
		bson = expected_type_info.type_(bson)

	# Deserialize into expected type
	if expected_type_info.type_ is dict:
		return bson

	elif expected_type_info.type_ is datetime:
		if not isinstance(bson, datetime):
			raise ValueError(f"{bson} not of the expected type datetime.\n\n# Document Context:\n{document_context}.")
		return bson
	
	elif expected_type_info.type_ is str:
		if not isinstance(bson, str): 
			raise ValueError(f"{bson} not of the expected type str.\n\n# Document Context:\n{document_context}")
		return str(bson)
	
	elif expected_type_info.type_ is float:
		try:
			bson = float(bson)
		except Exception as e:
			raise ValueError(f"{bson} not convertible to expected type float.\n\n# Document Context:\n{document_context}")
		return bson
	
	elif expected_type_info.type_ is bool:
		if not isinstance(bson, bool): 
			raise ValueError(f"{bson} not of the expected type bool.\n\n# Document Context:\n{document_context}")
		return bool(bson)
	
	elif expected_type_info.type_ is int:
		if not isinstance(bson, int): 
			raise ValueError(f"{bson} not of the expected type int.\n\n# Document Context:\n{document_context}")
		return int(bson)
	
	else:
		raise ValueError(f"Unable to deserialize invalid primitive type {expected_type_info.type_}.\n\n# Document Context:\n{document_context}")
	
def str_to_primitive(str_val: str, expected_type_info: TypeInfo, document_context: DocumentContext | None) -> Any:
	""" Converts a string representation to a primitive type based on the expected type information. """

	# Deserialize into expected type
	if expected_type_info.type_ is dict:
		try:
			# Evaluate string representation of dict
			return eval(str_val)
		except Exception as e:
			raise ValueError(f"{str_val} not convertible to expected type dict.\n\n# Document Context:\n{document_context}")

	elif expected_type_info.type_ is datetime:
		try:
			return datetime.fromisoformat(str_val)
		except Exception as e:
			raise ValueError(f"{str_val} not convertible to expected type datetime.\n\n# Document Context:\n{document_context}")
	
	elif expected_type_info.type_ is str:
		return str_val
	
	elif expected_type_info.type_ is float:
		try:
			return float(str_val)
		except Exception as e:
			raise ValueError(f"{str_val} not convertible to expected type float.\n\n# Document Context:\n{document_context}")
	
	elif expected_type_info.type_ is bool:
		str_val = str_val.lower()
		if str_val == "true":
			return True
		elif str_val == "false":
			return False
		else:
			raise ValueError(f"{str_val} not convertible to expected type bool.\n\n# Document Context:\n{document_context}")
	
	elif expected_type_info.type_ is int:
		try:
			return int(str_val)
		except Exception as e:
			raise ValueError(f"{str_val} not convertible to expected type int.\n\n# Document Context:\n{document_context}")
	
	else:
		raise ValueError(f"Unable to deserialize invalid primitive type {expected_type_info.type_}.\n\n# Document Context:\n{document_context}")

