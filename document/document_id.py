from typing import Generic, TypeVar

from .random_id import random_id
from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from .document import Document


T = TypeVar('T', bound='Document')

class DocumentId(str, Generic[T]):
	""" Used for both a document's own _id field.
	And for foreign keys. When using as a ForeignKey, do: ForeignKey[DocumentClass] """
	def __new__(cls, _id: str | None = None):
		if not _id:
			_id = random_id(24)
		instance = super().__new__(cls, _id)
		return instance
	
	@classmethod
	def with_prefix(cls, prefix: str):
		if len(prefix) != 3:
			raise ValueError("DocumentId prefix should be 3 characters.")
		return DocumentId(prefix + random_id(24))
	
NEW_DOCUMENT_ID = DocumentId("new")
ADMIN = DocumentId("admin") # Use this as the owner for system documents
PUBLIC = DocumentId("public") # Use this to allow a document to be accessible without authentication.