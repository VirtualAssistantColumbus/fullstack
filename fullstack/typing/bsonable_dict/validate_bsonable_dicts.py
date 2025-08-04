from ..bsonable_dataclass.bsonable_dataclass import BsonableDataclass
from .bsonable_dict import BsonableDict, __value__, __key__


def validate_bsonable_dicts(primitives: list[type], pseudo_primitives: list[type], all_bsonable_dataclasses: list[type[BsonableDataclass]], bsonable_dicts: list[type[BsonableDict]]):
	""" Validates that all BsonableDicts follow the rules for their key and value types. """
	# Only primitives and pseudoprimitves can be used as keys. Keys have to be serialized into strings in MongoDb.
	valid_key_types = tuple(primitives + pseudo_primitives)
	
	# Any bsonable type can be used for values, including abstract bsonable dataclasses
	valid_value_types = tuple(primitives + pseudo_primitives + all_bsonable_dataclasses + bsonable_dicts)
	
	for bsonable_dict in bsonable_dicts:
		if not hasattr(bsonable_dict, __key__):
			raise ValueError(f"BsonableDict '{bsonable_dict.__name__}' is missing required __key_type__ attribute.")
		if not hasattr(bsonable_dict, __value__):
			raise ValueError(f"BsonableDict '{bsonable_dict.__name__}' is missing required __value_type__ attribute.")
		
		if not issubclass(bsonable_dict.__key__, valid_key_types):
			raise ValueError(f"BsonableDict '{bsonable_dict.__name__}' uses a invalid key type {bsonable_dict.__key__.__name__}.")
		if not issubclass(bsonable_dict.__value__.type_expectation.type_info.type_, valid_value_types):
			raise ValueError(f"BsonableDict '{bsonable_dict.__name__}' uses a non-serializable value type {bsonable_dict.__value__.type_expectation.type_info.type_.__name__}.")