"""
Document module for managing document operations and database interactions.

This module provides functionality for:
- Document CRUD operations
- MongoDB integration
- Document context management
- API interfaces for document operations
"""

from .document_id import DocumentId, ADMIN, PUBLIC, NEW_DOCUMENT_ID
from .document_info import DocumentInfo, listDocumentInfo
from .document import Document
from .update_pointer import update_pointer_value, deference_pointer
from .modify_bson_fields import add_field, rename_field, delete_field