from abc import ABC, abstractmethod
from typing import ClassVar

from flask import Response, make_response
from flask_login import current_user

from ...typing.fields.schema_config import SchemaConfig
from ...utilities.special_values import AUTO
from ..htmx.htmx_request import htmxmethod
from .alerts import snackbar_error_message_
from .element_ import Element_, UniqueElement_, draw
from ..utilities.html import Html
from ..utilities.syntax_highlighting import comment


class AddElement(Element_):
	
	element_to_add_: Element_

	def draw(self) -> Html:
		return Html(f"""
			<div hx-swap-oob="beforeend:body"> { comment("Using beforeend only swaps inner html, which requires that we use a wrapper div.") }
				{ draw(self.element_to_add_) }
			</div>
		""")

def get_additive_element(element_to_add_: Element_) -> Element_:
	""" Returns an element that adds the inner element to the end of the page. """
	return AddElement(element_to_add_=element_to_add_)

def get_subtractive_element(element_id: str) -> Element_:
	""" Returns HTML that removes the element with the specified id. """
	return RemoveDiv(element_id)

class RemoveDiv(Element_):
	""" An element which clears the div with the specified id. """
	div_id: str
	def draw(self) -> Html:
		return Html(f"""
			<div id="{self.div_id}" hx-swap-oob="delete"></div>
		""")
	
def add_modal(modal_: 'Modal_') -> Response:
	content = Html(f"""
		<div hx-swap-oob="beforeend:body"> { comment("Using beforeend only swaps inner html, which requires that we use a wrapper div.") }
			{ draw(modal_) }
		</div>
	""")
	return make_response(content)

class Modal_(UniqueElement_, ABC):
	""" A non-stateful modal designed to be added and removed from any page dynamically. """

	__type_id__ = AUTO
	__login_required__: ClassVar[bool] = True # Is login required to show this modal?
	__width__: ClassVar[str] = "sm:max-w-lg"
	__height__: ClassVar[str] = "sm:max-h-[80vh]"

	is_visible: bool = SchemaConfig(kw_only=True, default=True)
	close_htmx: str | None = SchemaConfig(kw_only=True, default=None)

	def draw(self) -> Html:
		if self.close_htmx:
			close_htmx = self.close_htmx
		else:
			close_htmx = str(self.htmx_remove_self_from_page())
		
		return Html(f"""
			<div
				id="{ self.element_id() }"
				hx-swap-oob="true"
				class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
				{ close_htmx }
				{ "" if self.is_visible else "hidden" }
			>
				<!-- Modal container -->
				<div class="fixed inset-0 z-10 overflow-y-auto">
					<div class="flex min-h-full items-center justify-center p-4 text-center">
						<!-- Modal content -->
						<div 
							class="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full {self.__width__} {self.__height__} sm:p-6"
							onclick="event.stopPropagation()"
						>
							{ self.inner_html() }
						</div>
					</div>
				</div>
			</div>
		""")

	@abstractmethod
	def inner_html(self) -> str:
		raise NotImplementedError

	@htmxmethod(login_required=False) # Enforce login requirements within the modal
	def htmx_append_self_to_page(self) -> Html:
		""" Adds the modal to the end of the body. """
		if type(self).__login_required__: # Important: You must check against the modal_ type, not the modal_ itself. The modal_ itself can be manipulated, but the type definition cannot be.
			# Check authentication with flask_login
			if not current_user.is_authenticated:
				return draw(snackbar_error_message_("Login required to access this functionality."))

		return Html(f"""
			<div hx-swap-oob="beforeend:body"> { comment("Using beforeend only swaps inner html, which requires that we use a wrapper div.") }
				{ draw(self) }
			</div>
		""")

	@htmxmethod(login_required=False)
	def htmx_remove_self_from_page(self) -> Html:
		"""Removes the modal from the page using HTMX out-of-band swap."""
		return draw(RemoveDiv(self.element_id()))

	@htmxmethod(login_required=False)
	@staticmethod
	def htmx_remove_modal_from_page(modal_id: str) -> Html:
		"""Removes the modal from the page using HTMX out-of-band swap."""
		return draw(RemoveDiv(modal_id))