from typing import TypeVar


T = TypeVar('T')

def get_all_subclasses(cls: type[T]) -> set[type[T]]:
    """Get all subclasses of a class, including indirect subclasses.
    
    This implementation ensures we find all subclasses by:
    1. Getting immediate subclasses
    2. Recursively getting subclasses of those subclasses
    3. Using a copy of the set when iterating to avoid modification during iteration
    """
    subclasses = set()
    # Get immediate subclasses
    for subclass in cls.__subclasses__():
        # Add the immediate subclass
        subclasses.add(subclass)
        # Recursively get subclasses of this subclass
        subclasses.update(get_all_subclasses(subclass))
    return subclasses