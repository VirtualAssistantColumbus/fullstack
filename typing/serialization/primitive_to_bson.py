from datetime import datetime
from typing import Any

from .validate_primitive_dict import validate_primitive_dict


def primitive_to_bson(obj: Any) -> Any:
	""" Converts a primitive object to its BSON representation. """
	if type(obj) is dict:
		validate_primitive_dict(obj)
		return obj
	if type(obj) is list:
		# TODO: Validate sub type
		from .obj_to_bson import obj_to_bson
		return [obj_to_bson(item) for item in obj]
	elif type(obj) is datetime:
		return obj # The Python mongo driver will automatically handle datetimes, so you should pass them as datetime objects
	elif type(obj) is str:
		return obj
	elif type(obj) is float:
		return obj
	elif type(obj) is int:
		return obj
	elif type(obj) is bool:
		return obj
	else:
		raise TypeError(f"Unable to convert invalid primitive type {type(obj).__name__} to BSON.")
	
def primitive_to_str(obj: Any) -> str:
	""" Converts a primitive object to its string representation. """
	if type(obj) is dict:
		validate_primitive_dict(obj)
		return str(obj)
	if type(obj) is list:
		raise NotImplementedError
	elif type(obj) is datetime:
		return obj.isoformat()
	elif type(obj) is str:
		return obj
	elif type(obj) is float:
		return str(obj)
	elif type(obj) is int:
		return str(obj)
	elif type(obj) is bool:
		return str(obj).lower()
	else:
		raise TypeError(f"Unable to convert invalid primitive type {type(obj).__name__} to string.")
