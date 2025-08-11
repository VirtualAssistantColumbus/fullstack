from dataclasses import dataclass, field

from ..typing.pseudo_primitives.typed_list import TypedList

from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from .document import Document


@dataclass
class DocumentInfo:
	cls: 'type[Document]'
	cls_name: str
	collection_name: str
	reference_fields: 'dict[str, type[Document]]' = field(default_factory=dict)

class listDocumentInfo(TypedList[DocumentInfo]):
	__allowed_types__ = (DocumentInfo, )

	def type_id_to_cls(self, type_id: str) -> 'type[Document]':
		for document_info in self:
			if document_info.cls.__type_id__ == type_id:
				return document_info.cls
		raise ValueError(f"Document class with type id {type_id} not found in our document info registry.")

	def cls_name_to_cls(self, cls_name: str) -> 'type[Document]':
		for document_info in self:
			if document_info.cls_name == cls_name:
				return document_info.cls
		raise ValueError(f"Document class with class name {cls_name} not found in our document info registry.")
	
	def collection_name_to_cls(self, collection_name: str) -> 'type[Document]':
		for document_info in self:
			if document_info.collection_name == collection_name:
				return document_info.cls
		raise ValueError(f"Document class with collection name {collection_name} not found in our document info registry.")
	
	# DEPRECATED: To remove
	# def get_foreign_key_type_info(self, type_) -> TypeInfo:
	# 	""" Pass in 
	# 	Returns TypeInfo for a type annotation whose origin is ForeignKey.
	# 	The reason we have this within DocumentInfoRegistry is so that we can dereference the ForwardRefs in ForeignKey. """

	# 	origin = get_origin(type_)
	# 	if origin is not DocumentId:
	# 		raise

	# 	args = get_args(type_) # Get arguments from the original annotation, not the origin
	# 	if not args:
	# 		raise MongoSetupError
	# 	if len(args) != 1:
	# 		raise MongoSetupError
	# 	type_parameter = args[0]
		
	# 	# Parse the type parameter into the original Document class
	# 	if inspect.isclass(type_parameter) and issubclass(type_parameter, Document):
	# 		referenced_document_cls = type_parameter
	# 	elif isinstance(type_parameter, ForwardRef):
	# 		# If it's a forward annotation, we look up the class by name
	# 		# Look up the class by its name
	# 		referenced_document_cls_name = type_parameter.__forward_arg__
	# 		referenced_document_cls = self.cls_name_to_cls(referenced_document_cls_name)
	# 	else:
	# 		raise MongoSetupError

	# 	if not issubclass(referenced_document_cls, Document): # Let's just do an extra sanity check...
	# 		raise ValueError
			
	# 	return TypeInfo(
	# 		type_=DocumentId,
	# 		sub_type=referenced_document_cls
	# 	)