from .document_id import DocumentId

from ..typing import type_registry


def delete_user(user_id: DocumentId):
    """ Deletes all user data. """
    for document_info in type_registry.document_info_list:
        document_info.cls.db_delete_documents_for_owner(user_id)
    
    # Todo: How do you delete the user object itself?
    # UserModel.db_delete_many({ "_id": user_id })