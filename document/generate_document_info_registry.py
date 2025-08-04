from ..utilities.setup_error import SetupError
from ..utilities.special_values import ABSTRACT
from ..typing.serialization.vars import __skip_document_registration__
from .generate_collection_references import populate_reference_fields
from ..typing.registration.get_all_subclasses import get_all_subclasses
from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from .document_info import listDocumentInfo


def generate_document_info_registry() -> 'listDocumentInfo':
	""" 
	Uses introspection to find all subclasses of Document, then creates a mapping from class.__name__ to actual class type.
	
	In the process, we validate:
	- All Document classes have unique class names
	- All non-abstract Document classes define a collection name
	- All collection names are unique across Document classes

	TODO: Update this to look at nested types for foreign keys
	"""
	from .document_info import DocumentInfo, listDocumentInfo
	from .document import Document
	document_classes = get_all_subclasses(Document)
	
	unique_class_names = set()
	unique_collection_names = set()

	document_info_list = listDocumentInfo()
	for document_class in document_classes:
		
		# Enfore unique class names
		if document_class.__name__ in unique_class_names:
			raise SetupError(f"Document class name {document_class.__name__} already exists.")
		unique_class_names.add(document_class.__name__)
		
		# # Skip user-bound documents
		# if issubclass(document_class, UserScopedDocument):
		# 	continue
		
		# Enforce all document classes must define a collection name (even if it's just ABSTRACT).
		# Make sure to check the class attr (from __dict__), and not any inherited attributes
		if not "__collection_name__" in document_class.__dict__:
			raise SetupError(f"Document class {document_class.__name__} does not define a collection_name. For abstract documents, use ABSTRACT.")
		
		collection_name = document_class.__dict__["__collection_name__"]

		# Skip abstract document classses.
		if collection_name == ABSTRACT:
			continue
		
		# Skip document classes with "__skip_document_registration__"
		if hasattr(document_class, __skip_document_registration__):
			continue

		# Enfore unique collections names
		if collection_name in unique_collection_names:
			raise SetupError(f"Collection name {document_class.__collection_name__} defined in Document class {document_class.__name__} already exists.")
		
		# Enforce get_owner
		if not "fk_user_id" in document_class.__bsonable_fields__ and not "get_owner" in document_class.__dict__:
			raise SetupError(f"Document class {document_class.__name__} does not have a way to assert its owner. Documents without fk_user_id should implement get_owner method.")

		unique_collection_names.add(document_class.__collection_name__)

		# Create DocumentInfo and add to registry
		document_info = DocumentInfo(
			cls=document_class,
			cls_name=document_class.__name__,
			collection_name=document_class.__collection_name__
		)
		document_info_list.append(document_info)
	
	# After all DocumentInfo have been created, populate each with their references.
	populate_reference_fields(document_info_list)

	return document_info_list