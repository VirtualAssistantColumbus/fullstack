from typing import Any

from ...utilities.logger import logger

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...document.document_context import DocumentContext


__collection_name__ = "__collection_name__"
__type_id__ = "__type_id__"
__true_class__ = "__true_class__"
__skip_document_registration__ = "__skip_document_registration__"

def get_type_id(bson: Any, document_context: 'DocumentContext | None') -> str | None:
    """ Get the type_id from the bson, if present. """
    
    if not isinstance(bson, dict):
        return None
    
    type_id = bson.get(__type_id__, None)
    if not type_id:
        logger.warning(f"Warning: Bson did not assert a __type_id__.\n{document_context}")
        return None
    
    if not isinstance(type_id, str):
        logger.warning(f"Warning: Bson asserted a __type_id__ that is not a string.'\n{document_context}")
        return None
    
    return type_id

def remove_type_id(bson: dict) -> dict:
    """ Removes the type id from the bson, if present. """
    if __type_id__ in bson:
        del bson[__type_id__]
    return bson