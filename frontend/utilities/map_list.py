from collections.abc import Sequence
from typing import Callable, TypeVar

from ..components.element_ import DrawableProtocol, Element_, Viewable, draw
from .html import Html


T = TypeVar('T')

def map_list(objs: list[T], pyx_func: Callable[[T], str]) -> str:
    return " ".join([pyx_func(obj) for obj in objs])

def draw_list(objs: Sequence[DrawableProtocol | Element_ | str]) -> Html:
    return Html("\n".join([
        obj if isinstance(obj, str) else draw(obj)
        for obj in objs
    ]))

def combine_list(objs: Sequence[str]) -> str:
    return "\n".join(objs)

def combine(*objs: str | Viewable) -> str:
    return "\n".join([draw(obj) if isinstance(obj, Viewable) else obj for obj in objs])
