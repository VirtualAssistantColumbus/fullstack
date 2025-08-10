import os
from typing import Callable

# Expose these at the module level
from ..utilities.setup_error import SetupError
from .htmx.htmx_request import htmxmethod, public_htmxmethod
from .htmx.client_supplied_field import ClientSuppliedField

# Check for required env variables
APP_PROTOCOL = os.environ.get("APP_PROTOCOL")
if not APP_PROTOCOL:
    raise SetupError("You must specify APP_PROTOCOL in your environment variables. Value should be 'http' or 'https'.")

API_HOST = os.environ.get("API_HOST")
if not API_HOST:
    raise SetupError("You must specify API_HOST in your environment variables. This will be the host where htmxmethod routes are registered.")

# Module state
app_protocol=APP_PROTOCOL
api_host: str = API_HOST

routes: dict[Callable, list[tuple[str, dict]]] = {}
head: str = "" # HTML to add to the head of all pages, do NOT wrap in head tags
script: str = "" # Script to add to the end of all pages, do NOT wrap in script tags

# Set Up: run this function after importing all routes and pages
from .framework.register_routes import register_flask_routes