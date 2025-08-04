from __future__ import annotations
from dataclasses import dataclass

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..typing.fields.field_path import FieldPath


@dataclass(frozen=True)
class DocumentContext:
    document_path: FieldPath
    """ The path of the current field relative to the document root. 
    List elements will be returned as [idx]. """
    
    document_id: str | None = None
    last_modified_by_global_version: str | None = None
    last_modified_by_app_id: str | None = None
    """ These will come from the document. """
    
    collection_name: str | None = None

    def replace(self, document_path: FieldPath | None = None) -> 'DocumentContext':
        new_context = DocumentContext(
            document_path=document_path if document_path else self.document_path,
            document_id=self.document_id,
            last_modified_by_global_version=self.last_modified_by_global_version,
            last_modified_by_app_id=self.last_modified_by_app_id,
            collection_name=self.collection_name
        )
        return new_context

    def subpath(self, field_name: str) -> 'DocumentContext':
        """ Returns a new DocumentContext with a modified document_path. """
        new_context = self.replace(
            document_path=self.document_path.subfield(field_name)
        )
        return new_context

    def subidx(self, idx: int) -> 'DocumentContext':
        """ Returns a new DocumentContext with a modified document_path. """
        new_context = self.replace(
            document_path=self.document_path.subidx(idx)
        )
        return new_context

    def __str__(self) -> str:
        """ Printable to logs. """
        output = f"Collection: {self.collection_name}\nDocument _id: {self.document_id}\nDocument path: {self.document_path}\nLast Modified by Global Version: {self.last_modified_by_global_version}\nLast Modified By App: {self.last_modified_by_app_id}"
        return output