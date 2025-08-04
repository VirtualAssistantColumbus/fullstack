from enum import StrEnum, auto

from ...typing.fields.schema_config import SchemaConfig
from ..framework.html_attr import HtmlAttr
from ..utilities.syntax_highlighting import html
from ..components.element_ import Element_, UniqueElement_
from ..utilities.map_list import draw_list


class MessageType(StrEnum):
    NEUTRAL = auto()
    ERROR = auto()

class SnackbarMessage(Element_):
    message: str
    message_type: MessageType = MessageType.NEUTRAL
    timeout_ms: int | None = 2000  # Default 2 second timeout, None for no timeout

    def draw(self) -> str:
        bg_color = "bg-gray-800"
        border_color = "border-gray-700"
        text_styles = "text-white font-medium"
        icon = """"""

        timeout_script = f"setTimeout(() => show = false, {self.timeout_ms})" if self.timeout_ms is not None else ""

        return html(f"""
            <div x-data="{{ show: true }}" x-show="show" x-init="{timeout_script}" x-transition:enter="transition ease-out duration-300" x-transition:enter-start="opacity-0 transform scale-90" x-transition:enter-end="opacity-100 transform scale-100" x-transition:leave="transition ease-in duration-300" x-transition:leave-start="opacity-100 transform scale-100" x-transition:leave-end="opacity-0 transform scale-90" class="max-w-xs w-full {bg_color} border {border_color} rounded-md shadow-sm p-3 flex items-center justify-between">
                <div class="flex items-center px-1">
                    {icon}
                    <p class="{text_styles} text-sm">{ self.message }</p>
                </div>
                <button @click="show = false" class="text-gray-400 hover:text-gray-500 focus:outline-none">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        """)

class SnackbarContainer_(UniqueElement_):
    __div_id__ = "base-alerts"
    messages: list[SnackbarMessage] = SchemaConfig(default_factory=list)

    def element_attr(self) -> HtmlAttr:
        return HtmlAttr(class_="fixed bottom-4 left-0 right-0 flex flex-col items-center space-y-2 z-50")

    def inner_html(self) -> str:
        return draw_list(self.messages)
    
def snackbar_error_message_(public_message: str | None = None):
    alert_message_ = SnackbarMessage(
        message=public_message or ""
    )
    return SnackbarContainer_([alert_message_])