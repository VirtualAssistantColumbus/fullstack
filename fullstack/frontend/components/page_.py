from abc import ABC, abstractmethod
from typing import ClassVar, Self
from urllib.parse import quote, unquote

from flask import json

from fullstack.typing.serialization.vars import remove_type_id

from ..utilities.html import Html
from ..framework.client_url import get_client_path
from ..framework.locator import HasUrl, Locator, url
from .element_ import Element_
from ...typing import __type_id__


def get_readable_url(url: str) -> str:
	""" This is a helper method just for internal debugging, useful for checking the state of the web app. """
	# URL decode everything except our encoded slashes
	json_str = unquote(url)
	# Now decode our forward slashes
	json_str = json_str.replace('%2F', '/')
	json_value = json.loads(json_str)
	return json.dumps(json_value, indent=4)

def path_to_bson(path: str) -> dict:
	# If the path does not exist, return an empty dict
	if not path:
		return {}
	
	# URL decode everything except our encoded slashes
	json_str = unquote(path)
	# Now decode our forward slashes
	json_str = json_str.replace('%2F', '/')
	json_value = json.loads(json_str)
	return json_value

def bson_to_path(bson: dict) -> str:
	""" Converts bson to path. """
	# If the bson is empty, do not add a path
	if not bson:
		return ""
	
	json_str = json.dumps(bson)
	# Replace forward slashes with encoded version, then URL encode everything else
	path = json_str.replace('/', '%2F')
	path = quote(path)
	return path

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
		return full_path.removeprefix(cls.get_path_prefix(leading_slash=True, trailing_slash=True))

	def page_title(self) -> str:
		return "Untitled"

	def to_full_url(self, include_http: bool = True) -> str:
		""" Returns the full url, including https://, subdomain, domain, and path. Depends on the website URL in environment variables. """
		return url(Locator(host=self.__host__, path=self.to_full_path()), include_http=include_http)

	def to_full_path(self):
		""" Serializes this object into a full path (including __path_id__) """
		json_value = self.to_bson()
		
		# Remove __type_id__
		remove_type_id(json_value)
		
		path = bson_to_path(json_value)

		# Add path prefix
		path_prefix = type(self).get_path_prefix(leading_slash=True, trailing_slash=True)
		full_path = path_prefix + path
		return full_path
	
	@classmethod
	def from_path(cls, path: str):
		""" Constructs a HasRoute from a URL. """
		bson = path_to_bson(path)

		# Add type id
		if not __type_id__ in bson:
			bson[__type_id__] = cls.__type_id__

		return cls.from_bson(bson, None)
	
	@classmethod
	def from_full_path(cls, full_path: str):
		# Remove path prefix
		path = cls.remove_path_prefix(full_path)
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