from types import UnionType
from typing import Annotated, ClassVar, Union, get_args, get_origin

from ..registration.type_info import TypeInfo


def get_type_info(type_: type) -> TypeInfo:
    """ Extracts type and subtype (if present) for a **single** (non-Union) type. """
    from ...document.document_id import DocumentId

    origin = get_origin(type_)

    if origin is Annotated:
        # From the origin, I want to extract the actual type, not the Annotated type. 
        # In other words, if the annotation was Annotated[list, SomeAnnotation], I want to return list
        base_type = get_args(type_)[0]
        type_info = get_type_info(base_type)
        return type_info
    elif origin in {Union, UnionType}:
        raise ValueError("This function should only be used for single types.")
    elif origin is DocumentId:
        args = get_args(type_) # Get arguments from the original annotation, not the origin
        type_parameter = args[0]
        return TypeInfo(
            type_=DocumentId,
            sub_type=type_parameter # Store the type parameter, which could be a ForwardRef or the actual type. We don't know at this point. To get the actual sub_type, use the DocumentInfoRegistry
        )
    elif origin is dict:
        # For now, we don't store any sub type information for a dict
        return TypeInfo(
            type_=dict,
            sub_type=None
        )
    elif origin is None:
        return TypeInfo(
            type_=type_,
            sub_type=None
        )
    elif origin is ClassVar:
        base_type = get_args(type_)[0]
        type_info = get_type_info(base_type)
        return type_info

    else:
        # Handle generic types that have a single type parameter
        # This works with list, tuple, set, frozenset, and your own custom generic types like ForeignKey
        args = get_args(type_)
        if not args:
            raise ValueError("Unable to get type info for type annotation with 'other' origin but no type arguments.")
        if len(args) != 1:
            raise ValueError("Unable to get type info for type annotation with 'other' origin and more than one type argument.")
        type_parameter = args[0]
        return TypeInfo(
            type_=origin,
            sub_type=type_parameter
        )


def get_type_info_list(type_annotation: type | UnionType) -> list[TypeInfo]:
    """ Take in a type_annotation (or type) and returns a list of the TypeInfos contained within it.
    
    For Unioned types, returns a multiple TypeInfos. For non-Unioned types, returns a single TypeInfo.
    
    (UnionTypes are technically instances of UnionType and not actually types. However, note that Python type-hinting systems interpret them correctly into their types when they are used as type hints.)
    """
    origin = get_origin(type_annotation)
    
    # 1/15/2025 update -- updated this to handle Annotated types
    if origin is Annotated:
        # From the origin, I want to extract the actual type, not the Annotated type. 
        # In other words, if the annotation was Annotated[list, SomeAnnotation], I want to return list
        base_type = get_args(type_annotation)[0]
        type_info = get_type_info_list(base_type)
        return type_info

    # For union types, return TypeInfo for each unioned type
    elif origin in {Union, UnionType}:
        unioned_types = type_annotation.__args__ #type: ignore
        type_info_list = []
        for unioned_type in unioned_types:
            type_info = get_type_info(unioned_type)
            type_info_list.append(type_info)
        return type_info_list
    
    # For single types, just return the TypeInfo for that
    else:
        # TODO: what is the type expectation of type_annotation at this point? Does it include a GenericAlias?
        return [get_type_info(type_annotation)] # type: ignore