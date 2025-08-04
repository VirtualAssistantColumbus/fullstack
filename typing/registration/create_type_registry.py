from typing import Any, Callable
from bidict import bidict

from ..bsonable_dataclass.validate_bsonable_dataclass_field_schema import validate_bsonable_dataclass_field_schema
from ..bsonable_dict.validate_bsonable_dicts import validate_bsonable_dicts
from .type_registry import TypeNameDict
from ...document.generate_document_info_registry import generate_document_info_registry
from ...utilities.logger import logger
"""
Documentation:
	- Note that if you have a field which is annotated with a parent class that has multiple subclasses, deserializing this field will rely on being able to find matching a type_id in our server code
"""

def create_type_registry(
		pseudo_primitives: list[type] | None = None,
		pseudo_primitive_to_bson: Callable[[Any], Any] | None = None,
		bson_to_pseudo_primitive: Callable[..., Any] | None = None
	) -> None:
	
	logger.debug("Creating type registry...")
	
	## Primitives ##
	# Note that primitive dicts must only store other primitive types
	# By placing a type here, we assert that we have defined a way to serialize and deserialize this type in primitive_to_bson and bson_to_primitive
	from datetime import datetime
	primitives_dict: bidict[str, type] = bidict({
		"dict": dict,
		"datetime": datetime,
		"str": str,
		"float": float,
		"int": int,
		"bool": bool
	})
	primitives_list = list(primitives_dict.values())
	
	## Pseudoprimitives ##
	# Set up pseudoprimitives
	if any(param is not None for param in (pseudo_primitives, pseudo_primitive_to_bson, bson_to_pseudo_primitive)):
		if not all(param is not None for param in (pseudo_primitives, pseudo_primitive_to_bson, bson_to_pseudo_primitive)):
			raise ValueError("If any of pseudo_primitives, pseudo_primitive_to_bson, or bson_to_pseudo_primitive are set, all must be set.")
	else:
		logger.debug("Using default pseudoprimitives.")
		from ..pseudo_primitives.default import _pseudo_primitives, _pseudo_primitive_to_bson, _bson_to_pseudo_primitive
		pseudo_primitives, pseudo_primitive_to_bson, bson_to_pseudo_primitive = _pseudo_primitives, _pseudo_primitive_to_bson, _bson_to_pseudo_primitive
	assert isinstance(pseudo_primitives, list)
	
	pseudo_primitives_dict: bidict[str, type] = bidict({cls.__name__: cls for cls in pseudo_primitives})
	pseudo_primitives_list = list(pseudo_primitives_dict.values())

	# After all relevant classes are imported, run registration
	# Register all types into the type_id_dict
	type_id_dict: bidict = bidict() # Stores all serializable types
	type_name_dict: TypeNameDict = TypeNameDict() # Stores *all* types, including abstract ones. Used for resolving forward refs
	# Add primitives
	type_id_dict.update(primitives_dict)
	type_name_dict.add_list(primitives_list)

	# Add pseudoprimitves
	# TODO validate type_id uniqueness across primitives and pseudoprimitives
	type_id_dict.update(pseudo_primitives_dict)
	type_name_dict.add_list(pseudo_primitives_list)
	
	# Register all BsonableDataclasses (including Documents) and BsonableDicts
	from ..bsonable_dataclass.register_bsonables_dataclasses import register_bsonable_dataclasses
	abstract_bsonable_dataclass_list, concrete_bsonable_dataclass_list = register_bsonable_dataclasses(type_id_dict, type_name_dict) # Uses introspection to register all subclasses of BsonableDataclass
	from ..bsonable_dict.register_bsonable_dicts import register_bsonable_dicts
	bsonable_dict_list = register_bsonable_dicts(type_id_dict, type_name_dict)
	
	# Log the abstract and concrete dataclasses for debugging
	logger.debug(f"Registered abstract BsonableDataclasses: {', '.join([cls.__name__ for cls in abstract_bsonable_dataclass_list])}")
	logger.debug(f"Registered concrete BsonableDataclasses: {', '.join([cls.__name__ for cls in concrete_bsonable_dataclass_list])}")
	
	# Generate a list of all bsonable types, which includes abstract types, and "type" itself
	all_bsonable_types = list(type_id_dict.values()) + [type] + abstract_bsonable_dataclass_list # Make sure you also add the list of abstract dataclasses (1/27/2025 update)
	
	# Validate that all BsonableDataclass fields and BsonableDict key/values
	validate_bsonable_dataclass_field_schema(type_name_dict, concrete_bsonable_dataclass_list) # Validate that all dataclass fields store a valid bsonable type
	validate_bsonable_dicts(
		primitives=primitives_list,
		pseudo_primitives=list(pseudo_primitives_dict.values()),
		all_bsonable_dataclasses=abstract_bsonable_dataclass_list + concrete_bsonable_dataclass_list,
		bsonable_dicts=bsonable_dict_list
	)

	# Generate DocumentInfoRegistry
	# TODO: Update document info registry to look at nested types for foreign keys
	document_info_registry = generate_document_info_registry()

	# Update the module-level type registry
	from .. import type_registry
	type_registry.document_info_list = document_info_registry
	type_registry.abstract_bsonable_dataclass_list=abstract_bsonable_dataclass_list
	type_registry.concrete_bsonable_dataclass_dict=concrete_bsonable_dataclass_list
	
	type_registry.pseudo_primitives=list(pseudo_primitives_dict.values())
	type_registry.pseudo_primitive_to_bson=pseudo_primitive_to_bson
	type_registry.bson_to_pseudo_primitive=bson_to_pseudo_primitive
	
	type_registry.primitives=list(primitives_dict.values())
	type_registry.type_id_dict=type_id_dict
	type_registry.type_name_dict=type_name_dict