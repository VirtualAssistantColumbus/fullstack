from dataclasses import asdict, dataclass
import json
from typing import ClassVar

from ..utilities.syntax_highlighting import js

""" 
To use:

1) Insert EventTrigger.client_script() into the framework script. (You'll need to write this for each EventTrigger, see the examples.)
2) In your response, add a header with key = 'HX-Trigger' and value equal to event_trigger.to_header_value().

Viola! Now you can trigger fully customizable Javascript events using HTMX!

Documentation: https://htmx.org/headers/hx-trigger/ 
"""


@dataclass
class EventTrigger:
    __event_name__: ClassVar[str]
    
    def to_dict(self) -> dict:
        json_value = { self.__event_name__: asdict(self) }
        return json_value

    def to_header_value(self) -> str:
        json_value = self.to_dict()
        return json.dumps(json_value)
    
    @classmethod
    def client_script(cls) -> str:
        """ Override this method to return the client-side JS needed to respond to this event. This needs to be preloaded (added to framework). """
        raise NotImplementedError

@dataclass
class Message(EventTrigger):
    __event_name__ = "showMessage"
    message: str

    @classmethod
    def client_script(cls) -> str:
        return js("""
            document.body.addEventListener("showMessage", function(evt){
                alert(evt.detail.message);
            });
        """)

@dataclass
class ClassUpdateEvent(EventTrigger):
    """ Use this to add or remove classes to a div. """

    __event_name__ = "classUpdate"

    div_id: str
    add_classes: list[str]
    remove_classes: list[str]

    @classmethod
    def client_script(cls) -> str:
        return js("""
            document.body.addEventListener("classUpdate", function(evt){
                const div = document.getElementById(evt.detail.div_id);
                if (div) {
                    if (evt.detail.remove_classes && evt.detail.remove_classes.length > 0) {
                        div.classList.remove(...evt.detail.remove_classes);
                    }
                    if (evt.detail.add_classes && evt.detail.add_classes.length > 0) {
                        div.classList.add(...evt.detail.add_classes);
                    }
                }
            });
        """)

@dataclass
class ClassUpdatesEvent(EventTrigger):
    """ Use this to add or remove classes from multiple divs. """

    __event_name__ = "classUpdates"

    class_update_events: list[ClassUpdateEvent]

    @classmethod
    def client_script(cls) -> str:
        return js("""
            document.body.addEventListener("classUpdates", function(evt){
                evt.detail.class_update_events.forEach(update => {
                    const div = document.getElementById(update.div_id);
                    if (div) {
                        if (update.remove_classes && update.remove_classes.length > 0) {
                            div.classList.remove(...update.remove_classes);
                        }
                        if (update.add_classes && update.add_classes.length > 0) {
                            div.classList.add(...update.add_classes);
                        }
                    }
                });
            });
        """)