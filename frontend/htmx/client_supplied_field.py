from dataclasses import dataclass
from enum import Enum, StrEnum, auto
from inspect import Parameter
from typing import Annotated, Any, TypeVar, get_origin

from ...typing.bsonable_dataclass.bsonable_dataclass import BsonableDataclass


T = TypeVar('T')

class RouteAnnotation(Enum):
    CLIENT_SUPPLIED_FIELD = auto()
    RAW_CLIENT_SUPPLIED_JSON = auto()

# Get client URL
class ClientUrl(str):
    pass

# GetClientSuppliedFormField
ClientSuppliedField = Annotated[T, RouteAnnotation.CLIENT_SUPPLIED_FIELD]
""" Use this annotation to indicate that a parameter should be extracted from client-submitted form data. """

class LookupLocation(StrEnum):
    FORM = auto()
    DATA = auto()

class Lookup(BsonableDataclass):
    """ Instructions that tell the server where to look for a specific peice of client-supplied data within the client request. """
    __type_id__ = "emphemeral:lookup"
    lookup_location: LookupLocation
    lookup_name: str
    """ The key (for data) or the name (for form). """

def form_lookup(name: str) -> Any:
    """ Alias Lookup to return as 'Any' so the type checker doesn't complain in your function signatures. 
    Pass in the name of the form field that you want the client to pass into the API request. """
    return Lookup(
        lookup_location=LookupLocation.FORM,
        lookup_name=name
    )

BY_PARAMETER_NAME = "PARAMETER_NAME"

@dataclass
class DataLookupBuilder:
    """ Instructions for data lookup, including js to render and Lookup.
    This obj is used temporarily. The js is rendered to the view, then discarded. 
    The nested lookup is sent over the wire and echoed back. """
    js: str
    """ The js to inject into hx-vals that will evaluate to the value we want to assign. """
    lookup: Lookup
    alias: str | None = None

def js_expression(js: str, alias: str | None = None) -> Any:
    """ Extract a js expression from the view. """
    # We will always construct the lookup_name to match with whatever we send the js value as
    if alias is None:
        lookup_name = BY_PARAMETER_NAME
    else:
        lookup_name = alias

    return DataLookupBuilder(
        js=js,
        alias=alias,
        lookup=Lookup(
            lookup_location=LookupLocation.DATA,
            lookup_name=lookup_name
        )
    )

def parameter_is_client_supplied_field(parameter: Parameter):
    """ Returns whether or not the annotation indicates that the field should be extracted from form data. """
    if get_origin(parameter.annotation) is Annotated and RouteAnnotation.CLIENT_SUPPLIED_FIELD in parameter.annotation.__metadata__:
        return True
    return False


# GetRawClientSuppliedJson
FROM_CLIENT: Any = "Form client" # The value of this does not matter and is not used. This is purely so you can set a default value in the function signature.

RawClientSuppliedJson = Annotated[dict, RouteAnnotation.RAW_CLIENT_SUPPLIED_JSON]
""" Use this annotation if you want to access the unflattened json dictionary directly. """

def parameter_is_raw_client_supplied_json(parameter: Parameter):
    return parameter.annotation is RawClientSuppliedJson