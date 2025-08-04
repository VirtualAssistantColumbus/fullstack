from bidict import bidict

from .bsonable_dict import BsonableDict
from ..registration.type_registry import TypeNameDict
from ..serialization.vars import __type_id__
from ..registration.get_all_subclasses import get_all_subclasses


def register_bsonable_dicts(type_id_dict: bidict[str, type], type_name_dict: TypeNameDict) -> list[type[BsonableDict]]:
    """ Returns:
        - dict of concrete BsonableDataclasses mapping type_id -> cls
        - list of abstract BsonableDataclasses
    
    We can validate that all of the items in this dictionary are MappableDataclasses, but we can't validate that all MappableDataclasses are in this dictionary. (Not immediately at least.) An error will only be raised when we actually try to serialize a MappableDataclass which has not been defined here. """
    
    # Get a list of all Bsonable subclasses except for BsonableDataclass and Document
    bsonable_dicts: set[type[BsonableDict]] = get_all_subclasses(BsonableDict)
    for bsonable_dict in bsonable_dicts:
        if not hasattr(bsonable_dict, __type_id__):
            raise ValueError(f"{bsonable_dict.__name__} does not have a __type_id__.")
        type_id = bsonable_dict.__type_id__
        
        # Ensure the type id is globally unique
        if type_id in type_id_dict:
            raise ValueError(f"{bsonable_dict.__name__} uses a duplicate type id '{type_id}' already used!")
        
        # Register the type into our global type dicts
        type_name_dict.add(bsonable_dict)
        type_id_dict[type_id] = bsonable_dict
    
    return list(bsonable_dicts)