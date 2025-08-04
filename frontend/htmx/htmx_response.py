from typing import Any
from flask import Response, json, make_response

from ..framework.locator import url
from ..components.element_ import DrawableProtocol
from ..framework.event_trigger import EventTrigger
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..components.page_ import Page_


def make_htmx_response(*args: Any) -> 'HtmxResponse':
    """
    Creates an HtmxResponse object, similar to Flask's make_response() but returns an HtmxResponse instead.
    
    This function accepts the same arguments you can return from a view function:
    - If no arguments are passed, it creates a new empty response
    - If one argument is passed, it's used as the response data
    - If multiple arguments are passed, they're passed as a tuple to the response constructor
    """
    if not args:
        return HtmxResponse()
    if len(args) == 1:
        args = args[0]
        
    # Get the Flask response first
    flask_response = make_response(args)
    
    # Create new HtmxResponse with same data and headers
    htmx_response = HtmxResponse(
        response=flask_response.response,
        status=flask_response.status,
        headers=flask_response.headers
    )
    
    return htmx_response

def add_url_update(htmx_response: 'HtmxResponse', app_: 'Page_'):
	htmx_response.add_url_update(url(app_))
	return htmx_response

def add_update_app_part(htmx_response: 'HtmxResponse', updated_part_: DrawableProtocol | str) -> Response:
	""" Convenience method to return a differential update. That is, we want to update only a portion of the page, but we also want to update the client URL to reflect the new state. 
	Pass in the PathableDataclass with the new state (this will be serialized into the URL).
	Pass in the part of the app that you want to replace in the client DOM.

	Ex: differential_update(app_, app_.settings_)
	"""
	if not isinstance(updated_part_, str):
		updated_part_ = updated_part_.draw()

	htmx_response.add_data(updated_part_)
	return htmx_response

class HtmxResponse(Response):
    def add_data(self, add_data: str | DrawableProtocol) -> None:
        """Add data to the response by appending it to existing data."""
        if not isinstance(add_data, str):
            add_data = add_data.draw()
            
        # Get current data as string
        current_data = self.get_data(as_text=True) or ""
        
        # Combine and set via Flask's Response methods
        new_data = current_data + str(add_data)
        self.set_data(new_data)

    def add_url_update(self, new_url: str) -> None:
        """ Modifies this response to update the client-side URL to the specified URL. """
        self.headers['HX-Push-Url'] = new_url

    def add_event_trigger(self, event: EventTrigger) -> None:
        """ Update this response to trigger a custom Javascript event! """
        self.headers['HX-Trigger'] = event.to_header_value()
    
    def add_event_triggers(self, events: list[EventTrigger]) -> None:
        """ Update this response to trigger multiple custom Javascript events at once. """
        # Combine all event triggers into a single JSON object
        combined_triggers = {}
        for event in events:
            event_dict = event.to_dict()
            combined_triggers.update(event_dict)
            
        # Set the combined triggers in the header
        self.headers['HX-Trigger'] = json.dumps(combined_triggers)

    def add_redirect(self, url: str):
        """ Add a header to trigger an HTMX redirect. """
        self.headers['HX-Redirect'] = url

    def add_refresh(self) -> None:
        """ Add a header to trigger a full page refresh. """
        self.headers['HX-Refresh'] = 'true'