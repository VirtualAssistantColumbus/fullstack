from abc import ABC, abstractmethod
from typing import Self

from flask import Response

from ...typing.fields.field_path import FieldPath
from ...typing.fields.schema_config import SchemaConfig
from ...utilities.logger import logger
from ...utilities.special_values import ABSTRACT

from ..framework.html_attr import HtmlAttr
from .element_ import Element_, UniqueElement_, draw
from ..utilities.html import Html

from .page_context import DATA_FRAME_CONTAINER, DATA_FRAME_CONTAINER_PAGE_FIELD_PATH, require_frame_container_context, update_frame_container_within_page

from ..utilities.map_list import draw_list
from ..htmx.htmx_request import htmxmethod


"""
Frame Containers and Frame Management

NOTE: This works in conjunction with post()

Frame containers provide a way to manage hierarchical UI components that can be dynamically updated through HTMX requests. 
Each frame container must know its location within the page hierarchy via its `page_field_path` property.

Key concepts:

1. Page Field Path
   - Every frame container tracks its location relative to the root Page_ using page_field_path
   - This path is encoded as a data attribute when the frame container is rendered
   - Example: If a frame container lives at page.content.main_frame, its page_field_path would reflect this hierarchy

2. HTMX Request Context
   - When any element initiates an HTMX request, the framework automatically:
	 a) Searches up the DOM tree for the nearest frame container
	 b) Extracts the container's page_field_path
	 c) Stashes this information into Flask's g object for access in route handlers
   - If no frame container is found, None is stored in g

3. Frame Operations
   - Frame containers support standard operations like:
	 - Adding new frames
	 - Removing frames
	 - Replacing frames
	 - All operations automatically handle URL updates and DOM synchronization

4. Composability
   - Frame containers can be nested and composed freely
   - IMPORTANT: Any element calling FrameContainer_ API methods must be used within a frame container context
   - Calling frame operations outside a frame container context will result in errors since the page_field_path cannot be determined

This design allows for flexible composition of UI components while maintaining strict control over component hierarchy and update behavior.
"""

class Frame_(UniqueElement_, ABC):
	""" Each frame within a frame container will always know the location of its FrameContainer relative to the page within which its contained. """

	@abstractmethod
	def breadcrumb_title(self) -> str:
		raise NotImplementedError

class FrameContainer_(Frame_, ABC):
	""" A FrameContainers can only be used within the context of a specific page, and must always be placed in a certain path relative to the page. """
	__type_id__ = ABSTRACT

	frames_: list[Frame_] = SchemaConfig(default_factory=list, kw_only=True)

	@classmethod
	@abstractmethod
	def frame_container_field_path(cls) -> FieldPath:
		""" Returns where, relative to the containing page, the FrameContainer will be used. A FrameContainers_ should always be aware of their own location within the page they are rendered in. """
		raise NotImplementedError

	def element_data(self) -> dict[str, str]:
		""" Include data- attributes on the element. """
		return { 
			DATA_FRAME_CONTAINER: "true",
			DATA_FRAME_CONTAINER_PAGE_FIELD_PATH: type(self).frame_container_field_path()
		}

	def base_frame(self) -> Frame_:
		if not self.frames_:
			logger.error(f"Attempted to get base frame from empty frame container {type(self).__name__}")
			raise ValueError(f"Cannot get base frame from empty frame container {type(self).__name__}")
		return self.frames_[0]

	def top_frame(self) -> Frame_:
		if not self.frames_:
			logger.error(f"Attempted to get top frame from empty frame container {type(self).__name__}")
			raise ValueError(f"Cannot get top frame from empty frame container {type(self).__name__}")
		return self.frames_[-1]
	
	# Internal
	@classmethod
	def default(cls) -> Self:
		raise NotImplementedError

	def add_frame(self, frame_: 'Frame_') -> None:
		self.frames_.append(frame_)

	def replace_top_frame(self, frame_: Frame_):
		self.frames_[-1] = frame_

	def remove_top_frame(self) -> None:
		if self.frames_:
			self.frames_.pop()

	def remove_frames_after(self, frame_idx: int):
		if frame_idx < 0:
			self.frames_ = []
		else:
			self.frames_ = self.frames_[:frame_idx + 1]
	
	# Frame operations
	@htmxmethod(show_loading=True)
	@classmethod
	def api_add_frame(cls, frame_: Frame_) -> Response:
		""" This gets information about the root Page AND the frame container from the frame_container_field_path, which details the relationship between those. """
		page_, frame_container_ = require_frame_container_context()

		assert isinstance(frame_container_, cls) # The frame container should match this cls
		frame_container_.add_frame(frame_)

		# Return the frame container and a URL update
		return update_frame_container_within_page(page_, frame_container_)

	@htmxmethod(show_loading=True)
	@classmethod
	def api_remove_top_frame(cls) -> Response:
		page_, frame_container_ = require_frame_container_context()
		
		assert isinstance(frame_container_, cls) # The frame container should match this cls
		frame_container_.remove_top_frame()

		return update_frame_container_within_page(page_, frame_container_)
	
	@htmxmethod(show_loading=True)
	@classmethod
	def api_replace_top_frame(cls, frame_: Frame_) -> Response:
		page_, frame_container_ = require_frame_container_context()
		assert isinstance(frame_container_, cls) # The frame container should match this cls
		
		frame_container_.replace_top_frame(frame_)
		
		return update_frame_container_within_page(page_, frame_container_)

	@htmxmethod(show_loading=True)
	@classmethod
	def api_remove_frames_after(cls, frame_idx: int) -> Response:
		page_, frame_container_ = require_frame_container_context()
		
		assert isinstance(frame_container_, cls) # The frame container should match this cls	
		frame_container_.remove_frames_after(frame_idx)
		
		return update_frame_container_within_page(page_, frame_container_)

class AddNewItem_(Element_):
	__type_id__ = "add_new_item_"
	
	text: str
	htmx_request: str

	def draw(self) -> Html:
		return Html(f"""
			<div class="mt-6 w-full bg-gray-50 hover:bg-gray-100 py-4 text-center transition-colors duration-300 cursor-pointer">
				<a 
					href="#"
					class="font-medium text-blue-600 hover:text-blue-800"
					{ self.htmx_request }
				>
					{ self.text }
				</a>
			</div>
		""")

def draw_list_item_(inner_html: Html, htmx_request: str, *, html_attr: HtmlAttr | None = None, include_caret: bool = True) -> Html:
	caret_svg = """
		<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-400 flex-shrink-0 ml-4" viewBox="0 0 20 20" fill="currentColor">
			<path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
		</svg>
	""" if include_caret else ""

	# Combine any custom html attributes with the predefined classes
	combined_classes = "flex items-center p-4 rounded-lg border border-gray-200 shadow-sm hover:bg-gray-50 transition-colors duration-300 cursor-pointer"
	if html_attr and html_attr.class_:
		combined_classes = f"{combined_classes} {html_attr.class_}"
		html_attr.class_ = None

	return Html(f"""
	<li
		class="{ combined_classes }"
		{ htmx_request }
		hx-trigger="click"
		{ html_attr }
	>
		<div class="flex-grow min-w-0">
			{ inner_html }
		</div>
		{ caret_svg }
	</li>
	""")

class TitledListItem_(Element_):
	__type_id__ = "list_item_"
	
	title: str
	subtitle: str
	htmx_request: str = ""
	max_height: str = "95px"  # Default max height of 200px

	def draw(self) -> Html:
		# Add gradient overlay only if content is actually truncated
		gradient_overlay = """
			<div 
				x-show="$refs.content.scrollHeight > $refs.content.clientHeight"
				class="absolute bottom-0 left-0 right-0 h-8"
				style="background: linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,1) 100%);"
			></div>
		""" if self.max_height else ""
		
		style = f'style="max-height: {self.max_height}; overflow: hidden;"' if self.max_height else ''
		
		inner_html = Html(f"""
			<div class="relative" x-data>
				<div x-ref="content" class="break-words whitespace-normal" {style}>
					{ 
						f'<span class="text-xl font-semibold text-gray-800">{ self.title }</span>' if self.title
						else '<span class="text-xl font-semibold text-gray-500">Untitled</span>'
					}
					<p class="text-sm text-gray-600 mt-1">{ self.subtitle }</p>
				</div>
				{ gradient_overlay }
			</div>
		""")
		return draw_list_item_(inner_html, self.htmx_request)

def draw_list_items_(
	title: str,
	subtitle: str,
	items_: list[TitledListItem_],
	add_new_item_: AddNewItem_
) -> Html:
	return Html(f"""
		<div class="container max-w-2xl mx-auto pt-4">
			<h2 class="text-2xl font-bold text-gray-900 mb-2">{ title }</h2>
			<p class="text-gray-600 mb-6">{ subtitle }</p>
			<ul class="space-y-4">
				{ draw_list(items_) }
			</ul>
			{ draw(add_new_item_) }
		</div>
	""")

class EditItemWrapper_(Element_):
	title: str
	content: str

	def draw(self) -> Html:
		return Html(f"""
			<div class="mb-6 max-w-2xl mx-auto">
				<h2 class="text-2xl font-bold text-gray-900 pt-3 pb-5">{ self.title }</h2>
				{ self.content }
			</div>
		""")

class EditItemSection_(Element_):
	title: str
	description: str
	content: str

	def draw(self) -> Html:
		return Html(f"""
			<div class="mb-5">
				<label class="block text-m font-medium text-gray">{ self.title }</label>
				<p class="text-sm text-gray-400 mt-2 mb-2 font-thin">{ self.description }</p>
				<div class="mt-2">
					{ self.content }
				</div>
			</div>
		""")
	
class ExpandableText_(Element_):
	inner_text_html: str
	collapsed_height: int = 112  # 28px * 4 lines (h-28 was previously hardcoded)

	def draw(self) -> Html:
		return Html(f"""
			<div 
				x-data="{{ 
					expanded: false,
					needsExpansion: false,
					init() {{
						// Check if content height exceeds collapsed height
						this.needsExpansion = this.$refs.content.scrollHeight > {self.collapsed_height};
						// Auto-expand if no expansion needed
						if (!this.needsExpansion) this.expanded = true;
					}}
				}}" 
				class="relative mb-6"
				:class="{{ 'overflow-hidden': !expanded, 'h-[{self.collapsed_height}px]': !expanded && needsExpansion }}"
			>
				<div 
					x-ref="content"
					class="text-gray-500 text-sm leading-relaxed"
					@click="!expanded && needsExpansion && (expanded = true)"
					:class="{{ 'cursor-pointer': !expanded && needsExpansion }}"
				>
					{ self.inner_text_html }
				</div>
				
				<!-- Gradient overlay -->
				<div 
					x-show="!expanded && needsExpansion"
					@click="expanded = true"
					class="absolute bottom-0 left-0 right-0 h-20 cursor-pointer"
					style="background: linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,0.9) 50%, rgba(255,255,255,1) 100%);"
				></div>
				
				<!-- Modified expand/collapse buttons -->
				<button 
					x-show="!expanded && needsExpansion"
					@click="expanded = true"
					class="absolute bottom-0 left-1/2 transform -translate-x-1/2 px-4 py-1 text-sm text-gray-500 hover:text-gray-700 pointer-events-none"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
					</svg>
				</button>
				<button 
					x-show="expanded && needsExpansion"
					@click="expanded = false"
					class="w-full text-center px-4 py-1 text-sm text-gray-500 hover:text-gray-700 mt-2"
				>
					<svg class="w-5 h-5 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"/>
					</svg>
				</button>
			</div>
		""")