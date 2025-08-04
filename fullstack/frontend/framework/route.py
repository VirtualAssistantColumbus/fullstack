from enum import StrEnum, auto

from .. import routes
from .locator import Locator


class Method(StrEnum):
    GET = auto()
    POST = auto()

def app_route(host: str, rule: str, *, methods: list[Method] | None = None, defaults: dict | None = None, strict_slashes: bool | None = None):
    """ Registers a vanilla Flask route. You should rarely need to use this. 
    To allow a route to work for any subdomain, use subdomain="<subdomain>". When you do this, the route must also accept a parameter called subdomain. This is a Flask thing.
    """
    kwoptions = {
        "host": host,
        "methods": [m.value for m in methods] if methods is not None else [Method.GET.value], # Flask will automatically default to "GET" anyway
        "defaults": defaults,
        "strict_slashes": strict_slashes
    }
    combined_options = kwoptions
    
    def decorator(f):
        if f not in routes:
            routes[f] = []
        routes[f].append((rule, combined_options))
        return f
    return decorator

def locator_route(locator: Locator, path_variables: list[str] | None = None, methods: list[Method] | None = None):
    # Combine path variables into a Flask rule string
    if path_variables is None:
        path_variables = []
    
    rule = locator.path
    for path_var in path_variables:
        if not path_var.startswith("<") or not path_var.endswith(">"):
            raise ValueError(f"Path variable {path_var} must be wrapped in angle brackets (e.g. '<path_var>')")    
        rule += f"/{path_var}"

    return app_route(host=locator.host, rule=rule, methods=methods)