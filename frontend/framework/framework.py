from enum import StrEnum

from .html_attr import HtmlAttr
from ..components.alerts import SnackbarContainer_
from ..components.element_ import UniqueElement_, draw
from ..framework.event_trigger import ClassUpdateEvent, ClassUpdatesEvent
from ..utilities.html import Html
from ..utilities.syntax_highlighting import comment

class Z(StrEnum):
	""" Global z variables """
	MODAL = "z-40"
	LOADING = "z-50"

class LoadingIndicator(UniqueElement_):
	__type_id__ = "loading_indicator"
	__div_id__ = "loading-indicator"

	def element_attr(self) -> HtmlAttr:
							   # htmx-indicator is a Tailwind utility that displays as "hidden" by default and "" when loading
		return HtmlAttr(class_=f"htmx-indicator fixed inset-0 {Z.LOADING} flex items-center justify-center bg-black/25 pointer-events-none")

	def inner_html(self) -> Html:
		return Html("""
			<!-- Loading spinner -->
			<div class="inline-block h-16 w-16 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent motion-reduce:animate-[spin_1.5s_linear_infinite]" role="status">
				<span class="sr-only">Loading...</span>
			</div>
		""")
	
	@classmethod
	def show_while_loading(cls) -> str:
		""" Returns loading attr as a str. """
		return str(cls.get_loading_attr())
	
	@classmethod
	def get_loading_attr(cls) -> HtmlAttr:
		""" Returns an attribute you can add to your HTMX request which will cause the loading indicator to show while the request is loading. The targeted element must also have the class htmx-indicator on it. """
		return HtmlAttr(hx_indicator=f"#{cls.__div_id__}")

def draw_framework(content: Html, replace_state: str | None = None, *, title: str | None = None, icon_path: str | None = None, debug_banner_content: str | None = None) -> Html:
	"""Framework function that can accept either a Page_ object or Html content with optional title/icon.
	
	Args:
		content: Html content to display
		replace_state: Optional URL to update browser state with
		title: Optional page title
		icon_path: Optional path to favicon
		debug_banner_content: Optional content for debug banner
	"""
	
	# Original function implementationd
	from .. import head, script
	
	# Set defaults
	if not title:
		title = "Untitled"
	if not icon_path:
		icon_path = ""
	
	# Note that you don't need to push a URL change, because the user will already be on that url
	return Html(f"""
		<!DOCTYPE html>
		<html lang="en">
		<head>
			<meta charset="UTF-8">
			<meta name="viewport" content="width=device-width, initial-scale=1.0">
			<!-- Branding -->
			<title>{ title }</title>
			<link rel="icon" type="image/x-icon" href="{icon_path}">
			
			<!-- Required scripts -->
			<script src="https://unpkg.com/htmx.org@2.0.2"></script> { comment("HTMX") }
			<script src="https://unpkg.com/hyperscript.org@0.9.12"></script>
			
			<!-- Inject custom head -->
			{ head }
		</head>
		<body>
			<div id="main" hx-swap-oob="true"> { comment("Wrap the page contents in a main div with hx-swap-oob so that returning the full page will replace page contents.") }
				{ draw(LoadingIndicator()) }
				{ content }
				{ draw(SnackbarContainer_([])) }
				<!-- Update browser URL to reflect App state. Include this within the main div as we want this to be swapped in with full page swaps. -->
                {f'<script>window.history.replaceState({{}}, \'\', \'{replace_state}\');</script>' if replace_state else ''}
			</div>
			<script>
				document.addEventListener('htmx:load', (event) => {{
					Alpine.initTree(event.target);
				}});

				<!-- Allow HTMX to call external websites -->
				htmx.config.selfRequestsOnly = false
				htmx.config.withCredentials = true

				<!-- Custom HTMX Events -->
				{ ClassUpdateEvent.client_script() }
				{ ClassUpdatesEvent.client_script() }

				<!-- Custom script -->
				{ script }
			</script>
		</body>
		</html>
	""")