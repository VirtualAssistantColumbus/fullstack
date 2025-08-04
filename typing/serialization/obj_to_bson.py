from typing import Any

from ..bsonable_dataclass.bsonable_dataclass import BsonableDataclass
from ..bsonable_dict.bsonable_dict import BsonableDict
from .primitive_to_bson import primitive_to_bson
from .. import type_registry


def obj_to_bson(obj: Any) -> Any:
	"""
	Serializes Python object into Bson. See readme.txt.
	"""

	# Handle types from specific (complex) to general (simple)
	if isinstance(obj, type):
		type_id = type_registry.type_to_type_id(obj)
		if not type_id:
			raise TypeError(f"Type {obj} not registered for serialization.")
		return f"type_id={type_id}"
	
	elif isinstance(obj, BsonableDataclass):
		return obj.to_bson()
	
	elif isinstance(obj, BsonableDict):
		return obj.to_bson()
	
	# First try to catch primitives based on an exact type match. This should not allow for inheritance, and should be checked before we check pseudoprimitives, as some pseudoprimitives may inherit from a primitive.
	elif type(obj) in type_registry.primitives:
		return primitive_to_bson(obj)
	
	elif isinstance(obj, tuple(type_registry.pseudo_primitives)):
		return type_registry.pseudo_primitive_to_bson(obj)
	
	elif obj is None:
		return None

	else:
		raise TypeError(f"Type {type(obj)} not serializable.")