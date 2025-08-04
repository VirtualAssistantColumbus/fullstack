from pymongo.database import Database

from .document import Document
from .document_id import ADMIN, DocumentId
from ..utilities.special_values import ABSTRACT

## Consider deprecating

class LogDocument(Document):
    """ A Document meant for logging. Documents of this type will be stored and retrieved from mongo_log_db instead of mongo_db. """
    __type_id__ = ABSTRACT
    __collection_name__ = ABSTRACT

    @classmethod
    def get_db(cls) -> Database:
        from .mongo_db import create_mongo_log_db
        return create_mongo_log_db()

    def get_owner(self) -> DocumentId:
        return ADMIN
    
    @classmethod
    def db_delete_documents_for_owner(cls, user_id: DocumentId) -> None:
        # Don't do anything unless the user_id is SYSTEM
        if user_id != ADMIN:
            return
        raise NotImplementedError