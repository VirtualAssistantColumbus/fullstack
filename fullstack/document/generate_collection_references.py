import inspect
from typing import ForwardRef

from ..utilities.setup_error import SetupError
from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from .document_info import listDocumentInfo


def populate_reference_fields(document_info_registry: 'listDocumentInfo') -> None:
	""" Generate a registry that stores, for each Document class, the fields which reference other Document classes. """
	from .document_info import listDocumentInfo
	from .document_id import DocumentId
	from .document import Document
	
	# TODO: Need to look at nested fields for references
	
	for document_info in document_info_registry:
		reference_fields: dict[str, type[Document]] = {}
		for field_name, field_schema in document_info.cls.__bsonable_fields__.items():
			if field_name == "_id":
				# Skip the document's own id
				continue
			if field_schema.type_expectation.type_info.type_ is DocumentId:
				type_parameter = field_schema.type_expectation.type_info.sub_type
				# Parse the type parameter into the original Document class
				if inspect.isclass(type_parameter) and issubclass(type_parameter, Document):
					referenced_document_cls = type_parameter
				elif isinstance(type_parameter, ForwardRef):
					# If it's a forward annotation, we look up the class by name
					# Look up the class by its name
					referenced_document_cls_name = type_parameter.__forward_arg__
					referenced_document_cls = document_info_registry.cls_name_to_cls(referenced_document_cls_name)
				else:
					raise SetupError(f"Field '{field_name}' within document '{document_info.cls_name}' is a DocumentId but does not specify what document type it references.")

				# type_info = document_info_registry.get_foreign_key_type_info(field_schema.type_expectation.type_info.sub_type)
				# if not inspect.isclass(type_info.sub_type) or not issubclass(type_info.sub_type, Document): raise

				if not issubclass(referenced_document_cls, Document): raise
				reference_fields[field_name] = referenced_document_cls

		document_info.reference_fields = reference_fields