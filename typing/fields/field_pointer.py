# type: ignore

from typing import Any

from ..bsonable_dataclass.bsonable_dataclass import BsonableDataclass
from ...document.document_id import DocumentId
from .field_path import FieldPath
from .field_schema import FieldSchema
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...document.document import Document


class DocumentFieldPointer(BsonableDataclass):
    """ Points to a nested field within a specific document.
    Use this with external API calls to allow the client to specify what field they want to edit within a Document. 
    The field that is pointed to must have "allow_edit_by_pointer" specified as True in their schema config. """
    __type_id__ = "ephemeral:field_pointer"
    
    document_id: DocumentId
    field_path: FieldPath

    def __str__(self) -> str:
        return f"document_id('{self.document_id}').field_path('{self.field_path}')"
    
    def as_element_id(self) -> str:
        """ Return a version of this pointer that's usable as an html element id. """
        # Replace periods with underscores and ensure it starts with a letter
        return f"field_pointer_{self.document_id}_{self.field_path}".replace('.', '_')

    def document_cls(self) -> type['Document']:
        """ Returns the document class this points to. """
        from .. import type_registry
        document_cls = type_registry.document_info_list.type_id_to_cls(self.field_path.get_root_type_id())
        return document_cls

    @staticmethod
    def for_(document_id: DocumentId, containing_document_cls: type['Document'], *args: Any | FieldSchema) -> 'DocumentFieldPointer':
        """ Construct an InstanceFieldPointer by passing in document_id, the containing document cls, and a list of fields. """
        field_path = FieldPath.for_(containing_document_cls, *args)
        field_pointer = DocumentFieldPointer(
            document_id=document_id,
            field_path=field_path
        )
        return field_pointer
    
    def extend(self, *args: Any | FieldSchema) -> 'DocumentFieldPointer':
        """ Returns a new DocumentFieldPointer with a field path extended by the arguments (i.e. returns a pointer that points to a nested field within this pointer) """
        extended_field_path = self.field_path.extend(*args)
        return DocumentFieldPointer(
            document_id=self.document_id,
            field_path=extended_field_path
        )