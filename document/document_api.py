from typing import Any, TypeVar, Generic

from .document_id import DocumentId
from ..typing.fields.field_pointer import DocumentFieldPointer
from ..utilities.result import UpdateFieldResult


T = TypeVar('T')

class UserDocumentAPI(Generic[T]):
    def __init__(self, user_id: DocumentId) -> None:
        self.user_id = user_id

    def find_one_by_id(self, document_id: DocumentId) -> T | None:
        raise NotImplementedError
    
    def require_one_by_id(self, document_id: DocumentId) -> T:
        raise NotImplementedError
    
    def get_all_for_user(self) -> list[T]:
        raise NotImplementedError

    def update_one(self, document: T) -> None:
        raise NotImplementedError
    
    def delete_one(self, document_id: DocumentId) -> None:
        raise NotImplementedError

    def update_pointer_value(self, pointer: DocumentFieldPointer, new_value: Any) -> UpdateFieldResult:
        raise NotImplementedError