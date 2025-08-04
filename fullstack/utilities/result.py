from dataclasses import dataclass, field

from ..typing.fields.field_path import FieldPath

## Consider deprecating

@dataclass
class UpdateFieldResult:
    """ Returns the result of an operation. """
    success: bool
    field_path: FieldPath
    message: str | None = None

@dataclass
class UpdateDocumentResult:
    success: bool
    message: str | None = None
    update_field_results: list[UpdateFieldResult] = field(default_factory=list)