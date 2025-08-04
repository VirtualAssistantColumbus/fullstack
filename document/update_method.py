from enum import StrEnum, auto


class UpdateMethod(StrEnum):
    """ Describes the method in which something is updated. """
    INSERT = auto()
    UPDATE = auto()