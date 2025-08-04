from collections.abc import Sequence
from typing import Self, TypeVar, Generic, List, Iterable, overload


# Define a type variable T that can be any type
T = TypeVar('T')

class TypedList(Generic[T], Sequence[T]):
    """ NOTE: TypedList should not be used in conjunction with dataclass. This will cause issues with Mongoable serialization. 
    You should also not add any additional fields or modify the input parameters for the __init__ method. """
    
    __allowed_types__: tuple[type, ...]
    """ Element type must be specified by inheriting classes. """

    def __init__(self, initial_elements: Iterable[T] | None = None):
        """
        Initialize a typed list.

        :param element_type: The type of the elements that the list should hold.
        :param initial_elements: An optional iterable of initial elements to populate the list.
        """
        self._elements: List[T] = []

        if initial_elements:
            self.extend(initial_elements)
        
        self.__validate_list__()

    def __validate_list__(self) -> None:
        """ Override this method if you'd like to perform certain validation every time the list is modified. """
        pass

    def __check_type__(self, element: T):
        """
        Check whether the element is of the correct type.

        :param element: The element to check.
        :raises TypeError: If the element is not of the expected type.
        """
        if not isinstance(element, self.__allowed_types__):
            raise TypeError(f"Got invalid type {type(element).__name__}.")

    def append(self, element: T):
        """
        Append an element to the list after checking its type.

        :param element: The element to append.
        """
        self.__check_type__(element)
        self._elements.append(element)
        self.__validate_list__()

    def extend(self, elements: Iterable[T]):
        """
        Extend the list with multiple elements after checking their types.

        :param elements: An iterable of elements to append.
        """
        for element in elements:
            self.__check_type__(element)
        self._elements.extend(elements)
        self.__validate_list__()

    @overload
    def __getitem__(self, idxs: int) -> T: ...
    
    @overload
    def __getitem__(self, idxs: slice) -> Self: ...
    
    def __getitem__(self, idxs: int | slice) -> T | Self:
        """
        Get an item or a slice of items from the list.

        :param index: The index or slice of the item(s).
        :return: The item at the specified index or a new TypedList of items if a slice is provided.
        """
        if isinstance(idxs, slice):
            # Handle slice: return a new TypedList instance with the sliced elements
            return self.__class__(self._elements[idxs])
        else:
            # Handle single index: return the element at the given index
            return self._elements[idxs]

    def __setitem__(self, index: int, element: T):
        """
        Set an item in the list at a specified index after checking its type.

        :param index: The index where the item should be set.
        :param element: The new item to set at the specified index.
        """
        self.__check_type__(element)
        self._elements[index] = element
        self.__validate_list__()

    def __len__(self) -> int:
        """
        Get the length of the list.

        :return: The number of elements in the list.
        """
        return len(self._elements)

    def __iter__(self):
        """
        Get an iterator for the list.

        :return: An iterator over the elements of the list.
        """
        return iter(self._elements)

    def __str__(self) -> str:
        """
         a string representation of the list.

        :return: A string representation of the list.
        """
        return str(self._elements)

    def __add__(self, other: Self) -> Self:
        if not isinstance(other, TypedList) or self.__allowed_types__ != other.__allowed_types__:
            raise TypeError("Both lists must be TypedList subclass instances with the same element type")

        return self.__class__(self._elements + other._elements)

    def __contains__(self, item) -> bool:
        return item in self._elements

    def __reversed__(self):
        return reversed(self._elements)

# Example usage
# typed_list = TypedList(int, [1, 2, 3])
# print(typed_list)
# typed_list.append(4)
# print(typed_list)
# typed_list.append('a')  # This will raise a TypeError