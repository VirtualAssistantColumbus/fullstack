# Page context data keys
from dataclasses import dataclass

from flask import Response, g

from ...typing.fields.field_path import FieldPath
from ..framework.locator import url
from ..htmx.htmx_response import make_htmx_response
from .page_ import Page_
from .element_ import draw
from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from .frame_ import FrameContainer_


DATA_FRAME_CONTAINER = "data-frame-container"
DATA_FRAME_CONTAINER_PAGE_FIELD_PATH = "data-frame-container-page-field-path"

@dataclass
class FrameContext:
	page_field_path: FieldPath

@dataclass
class PageContext:
	""" Stores context about where on the page the request was triggered. """
	frame_context: FrameContext
	
def stash_page_context_into_g(page_context: PageContext):
	g.page_context = page_context
	
def get_page_context() -> PageContext:
	return g.page_context

def require_frame_container_context() -> tuple[Page_, 'FrameContainer_']:
	""" From the URL and page context, require that we can find the frame container within the page URL. """
	from .frame_ import FrameContainer_

	page_context = get_page_context()
	print(page_context.frame_context)

	# Lookup the page cls from the field path
	page_cls = page_context.frame_context.page_field_path.containing_cls()
	assert issubclass(page_cls, Page_)
	
	# Instantiate an instance of the page based on the client url
	page = page_cls.from_client_url()
	
	# Get the frame container from the page instance
	frame_container = page_context.frame_context.page_field_path.navigate_into(page)
	assert isinstance(frame_container, FrameContainer_)

	return page, frame_container

def update_frame_container_within_page(page_: Page_, frame_container_: 'FrameContainer_') -> Response:
	""" Redraw the updated frame container and update the page URL. """
	htmx_response = make_htmx_response(draw(frame_container_))
	htmx_response.add_url_update(url(page_))
	return htmx_response