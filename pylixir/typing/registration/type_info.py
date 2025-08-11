from dataclasses import dataclass
from typing import ForwardRef


@dataclass
class TypeInfo:
	""" Stores type information. If the type is a sequence, will the subtype will be stored within the subtype field.
	For example list[str] will produce: concrete_type = list, subtype = str
	"""
	type_: type
	sub_type: type | ForwardRef | None