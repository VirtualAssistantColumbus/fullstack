""" Use this value on the client-side to represent None. When we decode the request back in post(), this value will be replaced with Python's None. """

from typing import Any


CLIENT_NONE_VALUE = "None-9483ecbd-00d2-4fe9-a361-9ada403d5070-Application"

def to_nullable_client_value(value: Any) -> Any:
    if value is None:
        return CLIENT_NONE_VALUE
    return value
    
def from_nullable_client_value(value: Any) -> Any:
    if value == CLIENT_NONE_VALUE:
        return None
    return value