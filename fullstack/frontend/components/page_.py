from abc import ABC, abstractmethod
from typing import ClassVar, Self
from urllib.parse import quote, unquote, parse_qs, urlencode
from flask import json

from fullstack.typing.serialization.vars import remove_type_id

from ..utilities.html import Html
from ..framework.client_url import get_client_path
from ..framework.locator import HasUrl, Locator, url
from .element_ import Element_
from ...typing import __type_id__
from ...utilities.logger import logger

# Sentinel values for non-string primitives and complex types in URL parameters
URL_SENTINEL_START = ".~"
URL_SENTINEL_END = "~."

def get_readable_url(url: str) -> str:
	""" This is a helper method just for internal debugging, useful for checking the state of the web app. """
	# URL decode everything except our encoded slashes
	json_str = unquote(url)
	# Now decode our forward slashes
	json_str = json_str.replace('%2F', '/')
	json_value = json.loads(json_str)
	return json.dumps(json_value, indent=4)

def args_to_bson(args: dict) -> dict:
	"""Converts query string arguments dict to BSON dict.
	
	Reconstructs the original structure by detecting and parsing
	JSON-encoded values using the URL_SENTINEL prefix.
	"""
	if not args:
		return {}
	
	result = {}
	
	for key, value in args.items():
		if value.startswith(URL_SENTINEL_START) and value.endswith(URL_SENTINEL_END):
			# Value is bookended with sentinels - decode as JSON
			try:
				# Remove bookend sentinels and decode the JSON value
				json_str = value[len(URL_SENTINEL_START):-len(URL_SENTINEL_END)]  # Remove .~ prefix and ~ suffix
				# URL decode everything except our encoded slashes
				json_str = unquote(json_str)
				# Now decode our forward slashes
				json_str = json_str.replace('%2F', '/')
				parsed_value = json.loads(json_str)
				result[key] = parsed_value
			except (json.JSONDecodeError, ValueError):
				# If JSON parsing fails, treat as regular string (fallback)
				result[key] = value
		else:
			# No bookend sentinels - treat as regular string
			result[key] = value
	
	return result

def bson_to_args(bson: dict) -> dict:
	""" Converts BSON dict to query string arguments dict.
	
	Top-level parameters become query string arguments.
	Strings are stored as-is, all other types are prefixed with URL_SENTINEL.
	Returns a dictionary ready for use with from_args().
	"""
	if not bson:
		return {}
	
	args = {}
	
	for key, value in bson.items():
		if isinstance(value, str):
			# Strings are stored as-is (no encoding needed)
			args[key] = value
		else:
			# All other types (int, float, bool, None, dict, list, etc.) get JSON encoded with bookend sentinels
			json_str = json.dumps(value)
			# Replace forward slashes with encoded version to preserve them
			encoded_value = json_str.replace('/', '%2F')
			args[key] = f"{URL_SENTINEL_START}{encoded_value}{URL_SENTINEL_END}"
	
	return args

class Page_(Element_, HasUrl, ABC):
	""" Represents a destination which can be accessed by URL within our framework.

	- Capable of being recreated from URL
	- Capable of being represented as a URL
	
	Each page must have a __path_prefix__. 
	Path prefix should start with a slash (i.e. "/my_page")
	Path prefix should not be simply "/". To define a root-level path, use @route.
	
	NOTE: Make sure you add all Pages_ to register_flask_routes()
	"""

	__login_required__: ClassVar[bool]
	__host__: ClassVar[str]
	""" Host should be the full host, including both subdomain AND domain (i.e. mysubdomain.mydomain.com) """
	__path_prefix__: ClassVar[str]
	__favicon_path__: ClassVar[str] = ""

	# Optional
	def breadcrumb_title(self) -> str:
		return self.page_title()

	@classmethod
	def get_path_prefix(cls, *, leading_slash: bool, trailing_slash: bool) -> str:
		""" Returns the path prefix. """
		if not cls.__path_prefix__.startswith("/"):
			raise ValueError(f"Page {cls.__name__} path prefix must start with a slash! Got: {cls.__path_prefix__}")
			
		path_prefix = cls.__path_prefix__
		
		# Handle root path
		if cls.__path_prefix__ == "/":
			if trailing_slash or leading_slash:
				return "/"
			else:
				return ""
		# Handle all other paths
		else:
			if not leading_slash:
				path_prefix = path_prefix.removeprefix("/")
			if trailing_slash:
				path_prefix += "/"
			return path_prefix
			
	@classmethod
	def remove_path_prefix(cls, full_path: str) -> str:
		return full_path.removeprefix(cls.get_path_prefix(leading_slash=True, trailing_slash=False))

	def page_title(self) -> str:
		return "Untitled"

	def to_full_url(self, include_http: bool = True) -> str:
		""" Returns the full url, including https://, subdomain, domain, and path. Depends on the website URL in environment variables. """
		return url(Locator(host=self.__host__, path=self.to_full_path()), include_http=include_http)

	def to_args(self) -> dict:
		""" Returns this object as a dictionary of query string arguments.
		
		This is useful when you want to work with the arguments directly
		without constructing a URL string.
		"""
		json_value = self.to_bson()
		
		# Remove __type_id__
		remove_type_id(json_value)
		
		# Convert to args dict
		return bson_to_args(json_value)

	def to_full_path(self):
		""" Serializes this object into a full path (including __path_id__) """
		# Get args dict
		args = self.to_args()
		
		# Convert args to query string using built-in urlencode
		query_string = urlencode(args, doseq=False)
		path = f"?{query_string}" if query_string else ""

		# Add path prefix
		path_prefix = type(self).get_path_prefix(leading_slash=True, trailing_slash=False)
		full_path = path_prefix + path
		return full_path
	
	@classmethod
	def from_args(cls, args: dict):
		""" Constructs a Page_ from query string arguments.
		
		Args:
			args: Dictionary of query string arguments (e.g., from Flask's request.args)
		"""
		# args is already a dict, no need to parse
		bson = args_to_bson(args)
		
		# Add type id if not present
		if __type_id__ not in bson:
			bson[__type_id__] = cls.__type_id__
		
		return cls.from_bson(bson, None)
	
	@classmethod
	def from_path(cls, path: str):
		""" Constructs a Page_ from a URL path with query string.
		
		This method is kept for backward compatibility but is deprecated.
		Use from_args() instead for better clarity and performance.
		"""
		logger.warning("from_path() is deprecated. Use from_args() instead.")
		
		# Parse query string into args dict
		if '?' in path:
			query_part = path.split('?', 1)[1]
			args = parse_qs(query_part, keep_blank_values=True)
			# Convert lists to single values (parse_qs returns lists)
			args = {k: v[0] if v else "" for k, v in args.items()}
		else:
			args = {}
		
		# Convert args to BSON format and then construct the page
		bson = args_to_bson(args)
		
		# Add type id if not present
		if __type_id__ not in bson:
			bson[__type_id__] = cls.__type_id__
		
		return cls.from_bson(bson, None)
	
	@classmethod
	def from_full_path(cls, full_path: str):
		""" Constructs a Page_ from a full URL path. """
		logger.warning("Full path:")
		logger.warning(full_path)
		
		# Remove path prefix
		path = cls.remove_path_prefix(full_path)
		logger.warning(path)

		return cls.from_path(path)
	
	@classmethod
	def from_client_url(cls) -> Self:
		""" Constructs a Pathable based on the client's URL. This can only be used within the context of a Flask request with our post() decorator, which stashes the client's URL into Flask's g. """
		client_path = get_client_path()
		obj = cls.from_full_path(client_path)
		return obj
	
	@abstractmethod
	def inner_html(self) -> Html:
		raise NotImplementedError
	
	def draw(self) -> Html:
		""" Draws the full page. """
		from ..framework.framework import draw_framework

		return draw_framework(
			content=self.inner_html(),
			replace_state=self.to_full_path(),
			title=self.page_title(),
			icon_path=type(self).__favicon_path__
		)