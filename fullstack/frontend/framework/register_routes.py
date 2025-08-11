from flask import Flask, request
from flask_login import login_required

from ...utilities.setup_error import SetupError
from ...utilities.special_values import ABSTRACT
from ...typing.registration.get_all_subclasses import get_all_subclasses
from ..components.element_ import draw
from ..components.page_ import Page_
from .route import app_route
from ...utilities.logger import logger


def register_flask_routes(app: Flask):
    """ Registers all Flask routes. Make sure you import any routes here that you want Flask to know about. """
    from .. import routes
    
    # Register pages
    register_pages()

    # Actually register the routes with Flask using the global routes variable
    for func, rules in routes.items():
        for rule, options in rules:
            try:
                app.add_url_rule(rule, func.__name__, func, **options)
            except AssertionError as e:
                if "View function mapping is overwriting an existing endpoint function" in str(e):
                    print(f"Route registration error: {str(e)}")
                    print(f"Rule: {rule}")
                    print(f"Function: {func.__name__}")
                    print(f"Options: {options}")
                raise

def create_and_register_page_route(page_cls: type[Page_]) -> None:
    """ Generates a route for a page. """
    from .routable_cls_field_names import __login_required__

    rule = page_cls.get_path_prefix(leading_slash=True, trailing_slash=False)

    #temp
    logger.warning(f"Registering {page_cls} with rule {rule}")

    is_login_required = True # Default to True
    if hasattr(page_cls, __login_required__) and page_cls.__login_required__ == False:
        is_login_required = False

    if is_login_required:
        @app_route(host=page_cls.__host__, rule=rule, strict_slashes=False)
        @login_required # Make sure to apply the login required decorator first. This decorator returns the function wrapped in a login guard. We need to register this wrapper function, not the underlying one.
        def page_rt():
            page = page_cls.from_args(request.args)
            return draw(page)
    else:
        @app_route(host=page_cls.__host__, rule=rule, strict_slashes=False)
        def page_rt():
            page = page_cls.from_args(request.args)
            return draw(page)
    
    # Rename the function before applying login_required decorator.
    # login_required returns a wrapper function, we need to make sure to rename the underlying route function.
    page_rt.__name__ = f"page_rt_{page_cls.__name__}"
    
def register_pages() -> dict[str, type['Page_']]:
    # Import the global routes dict
    from .routable_cls_field_names import __path_prefix__, __login_required__
    
    page_registry: dict[str, type[Page_]] = {}
    page_classes = get_all_subclasses(Page_)
    for page_cls in page_classes:
        assert issubclass(page_cls, Page_)
        if not __path_prefix__ in page_cls.__dict__:
            raise SetupError(f"Page {page_cls.__name__} does not specify a __path_prefix__!")
        if page_cls.__path_prefix__ == ABSTRACT:
            continue
        if not __login_required__ in page_cls.__dict__:
            print(f"Page {page_cls.__name__} does not specify __login_required__, defaulting to True")
        if page_cls.__path_prefix__ in page_registry:
            raise ValueError(f"Page path: {page_cls.__path_prefix__} already used!")
        page_registry[page_cls.__path_prefix__] = page_cls

        # Generate a route per page
        create_and_register_page_route(page_cls)

    return page_registry