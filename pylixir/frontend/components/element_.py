from abc import ABC, abstractmethod
from typing import ClassVar, Protocol, runtime_checkable

from ..utilities.html import Html
from ..framework.html_attr import HtmlAttr
from ...typing.bsonable_dataclass.bsonable_dataclass import BsonableDataclass
from ...utilities.special_values import ABSTRACT, AUTO


@runtime_checkable
class DrawableProtocol(Protocol):
    """ Define a Protocol for any object that implements a draw method. """
    def draw(self) -> Html: ...

def draw(drawable: 'DrawableProtocol | None') -> Html:
    if drawable is None:
        return Html()
    return drawable.draw()

class Viewable(ABC):
    """ Asserts that a class is Viewable. """
    @abstractmethod
    def draw(self) -> Html:
        """ Returns HTML for the Viewable. """
        raise NotImplementedError

class Element_(BsonableDataclass, Viewable, ABC):
    """ Should implicitly return a single HTML element.
    
    Conventions:
        - If this Element is not meant to be persisted, do not specify a __type_id__ (Elements don't typically need to specify a __type_id__ as they aren't actually serialized (unless they are URL params))

    """
    
    __type_id__ = ABSTRACT
    
    @abstractmethod
    def draw(self) -> Html:
        pass

class NullElement(Element_):
    def draw(self) -> Html:
        return Html("")

EMBEDDED_DATA_INPUT_NAME = "embedded-data"

class TypedElement_(Element_, ABC):

    def element_type(self) -> str:
        """ By default, all blocks are divs. Override this if you'd like to use a different type of HTML element. """
        return "div"

    def element_class(self) -> str:
        return ""
    
    def element_data(self) -> dict[str, str]:
        """ Include data- attributes on the element. You should actually include the prefix data- on your keys. """
        return {}

    def element_attr(self) -> HtmlAttr:
        """ Optionally override this property if you'd like to specify the html attributes for the block. """
        return HtmlAttr()
    
    @abstractmethod
    def inner_html(self) -> Html:
        raise NotImplementedError

    # Render function
    def draw(self) -> Html:
        """ Return the element's html. """
        # Construct class html
        class_html = ""
        element_class = self.element_class()
        if element_class:
            class_html = f'class="{element_class}"'
        
        # Construct data html
        element_data_dict = self.element_data()
        element_data_html = " ".join(f'{key}="{value}"' for key, value in element_data_dict.items())

        return Html(f"""
            <{ self.element_type() } {class_html} { element_data_html } { self.element_attr() }>
                { self.inner_html() }
            </{ self.element_type() }>
        """)

class AddableElement_(TypedElement_, ABC):
    """ Elements of this type have a unique div id, but does not assert hx-swap-oob. This allows us to add or subtract it from the page, rather than swapping it. """

    __div_id__: ClassVar[str]

    def element_id(self) -> str:
        return type(self).__div_id__
    
    def draw(self) -> Html:
        """ Return the element's html. """
        return Html(f"""
            <{self.element_type()} id="{self.element_id()}" {self.element_attr()}>
                {self.inner_html()}
            </{self.element_type}>
        """)

class SwappableElement_(TypedElement_, ABC):
    """ An element with a specific id. """
    
    @abstractmethod
    def element_id(self) -> str:
        raise NotImplementedError

    # Render function
    def draw(self) -> Html:
        """ Renders the block using its properties. """

        # Construct class html
        class_html = ""
        element_class = self.element_class()
        if element_class:
            class_html = f'class="{element_class}"'
        
        # Construct data html
        element_data_dict = self.element_data()
        element_data_html = " ".join(f'{key}="{value}"' for key, value in element_data_dict.items())
        
        return Html(f"""
            <{self.element_type()} hx-swap-oob="true" id="{self.element_id()}" {class_html} { element_data_html } { self.element_attr() }>
                {self.inner_html()}
            </{self.element_type()}>
        """)
    
class UniqueElement_(SwappableElement_):
    """" All instances of UniqueElement share the same __div_id__. """
    # Specifiers
    __div_id__: ClassVar[str]

    def element_id(self) -> str:
        if type(self).__div_id__ == AUTO:
            return type(self).__name__
        return type(self).__div_id__