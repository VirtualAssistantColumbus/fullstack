from bidict import bidict

from .bsonable_dataclass import BsonableDataclass
from ..registration.type_registry import TypeNameDict
from ...utilities.special_values import ABSTRACT
from ..serialization.vars import __type_id__
from ..registration.get_all_subclasses import get_all_subclasses


def register_bsonable_dataclasses(type_id_dict: bidict[str, type], type_name_dict: TypeNameDict) -> tuple[list[type[BsonableDataclass]], list[type[BsonableDataclass]]]:
    """ Returns:
        - dict of concrete BsonableDataclasses mapping type_id -> cls
        - list of abstract BsonableDataclasses
    
    We can validate that all of the items in this dictionary are MappableDataclasses, but we can't validate that all MappableDataclasses are in this dictionary. (Not immediately at least.) An error will only be raised when we actually try to serialize a MappableDataclass which has not been defined here. """
    
    # Get a list of all Bsonable subclasses except for BsonableDataclass and Document
    bsonable_dataclasses: set[type[BsonableDataclass]] = get_all_subclasses(BsonableDataclass)
    concrete_bsonable_dataclass_list: list[type[BsonableDataclass]] = []
    abstract_bsonable_dataclass_list: list[type[BsonableDataclass]] = []
    for bsonable_dataclass in bsonable_dataclasses:
        if not hasattr(bsonable_dataclass, __type_id__):
            raise ValueError(f"{bsonable_dataclass.__name__} does not have a __type_id__.")
        type_id = bsonable_dataclass.__type_id__
        
        # Add all bsonable dataclasses to the type_name_dict
        type_name_dict.add(bsonable_dataclass)
        
        # Add abstract classes to list
        if type_id == ABSTRACT:
            abstract_bsonable_dataclass_list.append(bsonable_dataclass)
        
        # Add concrete classes to dict
        else:
            # Ensure the type id is globally unique
            if type_id in type_id_dict:
                raise ValueError(f"{bsonable_dataclass.__name__} uses a duplicate type id '{type_id}' already used!")
            
            # Add concrete dataclasses to type_id_dict
            type_id_dict[type_id] = bsonable_dataclass
            # Append it to our list of concrete bsonable dataclasses
            concrete_bsonable_dataclass_list.append(bsonable_dataclass)
    
    return (abstract_bsonable_dataclass_list, concrete_bsonable_dataclass_list)