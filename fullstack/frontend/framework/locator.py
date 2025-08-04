from abc import ABC, abstractmethod
from dataclasses import dataclass

from .. import app_protocol

class HasUrl(ABC):
	
	@abstractmethod
	def to_full_url(self, include_http: bool = True) -> str:
		"""  """
		raise NotImplementedError

@dataclass
class Locator(HasUrl):
	""" Defines the subdomain and path for a location within our app. """
	host: str
	path: str
	""" Path should include leading slash. """

	def to_full_url(self, include_http: bool = True) -> str:
		""" Returns a full URL given the subdomain and path. Path should include leading slash. """
		url = ""
		if include_http:
			url = app_protocol + "://"
		url += self.host + self.path
		return url

def url(has_url: HasUrl, *, add_subdomain: str | None = None, add_path_parts: list[str] | None = None, add_query_params: dict[str, str] | None = None, include_http: bool = True) -> str:
	""" Returns the full url for the page, including subdomain, domain (defined in env variables), and path. """
	url = has_url.to_full_url(include_http=include_http)
	
	if add_path_parts:
		url += "/" + "/".join(add_path_parts)
	if add_query_params:
		param_strings = [f"{key}={value}" for key, value in add_query_params.items()]
		url += "?" + "&".join(param_strings)
	return url