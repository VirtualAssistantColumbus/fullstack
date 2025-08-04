from flask import url_for


def url_for_func(func, **values):
    from .. import routes
    if func not in routes:
        raise ValueError(f"Could not build URL for function {func.__name__}. Function is not registered.")
    rule, _ = routes[func][0] # Use the first rule by default
    return url_for(func.__name__, **values)