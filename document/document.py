from datetime import datetime
from typing import Any, Self, TypeVar, overload
import time  # Add this import at the top

from pymongo.collection import Collection
from pymongo.typings import _Pipeline
from pymongo.database import Database
from pymongo import ReturnDocument

from ..typing.fields.field_pointer import DocumentFieldPointer
from ..typing.fields.field_schema import FieldSchema
from .document_id import DocumentId
from ..typing.bsonable_dataclass.bsonable_dataclass import BsonableDataclass
from ..typing.fields.field_path import FieldPath
from ..typing.fields.get_field_name import get_field_name
from ..typing.fields.schema_config import _DocumentSchemaConfig, DocumentSchemaConfig
from .update_method import UpdateMethod
from ..typing.serialization.obj_to_bson import obj_to_bson
from ..utilities.special_values import ABSTRACT
from .document_context import DocumentContext
from ..utilities.logger import logger
from ..typing.serialization.vars import __type_id__


T = TypeVar('T', bound="Document")

"""
Validation Behavior:

Both validation_func and document_validation_func will run for all fields when:
	- updating fields directly (via the db_update_field functions) AND 
	- when updating the entire document (validation_func will run as a result of reserialization in _validate_self() and document_validation_funcs will be run for each field in __before_saving__())
So if you need to validate a field independently, you can simply define it in these functions, and they will always be enforced. (A field must be configured to allow independent updates.)

If for some reaons, you need to validate at the document level, you can extend __before_saving__ for this purpose. This validation will only run when performing document-level updates.
"""

class Document(BsonableDataclass):
	""" A dataclass that implements this method can be saved to MongoDb as a document. 
	NOTE: ** WHEN INHERITING FROM MONGOABLE YOU MUST USE PYDANTIC'S DATACLASS INSTEAD OF PYTHON'S **
	You may also need to add config={"arbitrary_types_allowed": True} to the dataclass decorator.

	Retrieved objects will have the _id from the database. Newly created objects will be assigned a randomly generated _id unless you specify one specifically.
	"""
	# Class fields
	__type_id__ = ABSTRACT
	__collection_name__ = ABSTRACT

	@classmethod
	def get_collection_name(cls) -> str:
		if not cls.__collection_name__:
			raise ValueError(f"Collection name not defined for {cls}. __collection_name__ must be specified for type-bound document classes.")
		return cls.__collection_name__

	# Instance fields
	# Setting kw_only=True allows for subclasses to add other fields without the type checker complaining that non-default fields appear after default fields.
	_id: DocumentId = DocumentSchemaConfig(default_factory=DocumentId, kw_only=True)
	__version__: int = DocumentSchemaConfig(default=0, kw_only=True)
	__last_modified__: float | None = DocumentSchemaConfig(default=None, kw_only=True)
	""" Stores when we last updated this document in the db. """
	# __last_modified_by_app_id__: str | None = DocumentSchemaConfig(default=None, kw_only=True)
	# """ The app id of the app which last modified this document. """
	# __last_modified_by_app_version__: str | None = DocumentSchemaConfig(default=None, kw_only=True)
	# """ The app version that last modified this document. """
	
	# Get information about which mongo db and collection this Document is mapping to.
	# This is different for Document vs. LogDocument
	@classmethod
	def __class_getitem__(cls, user_id: DocumentId) -> type['Document']:
		""" Provides a way to override the collection name. """
		class UserContextualizedDocumentCls(cls):
			__user_id__ = user_id
		return UserContextualizedDocumentCls
	
	@classmethod
	def get_collection(cls) -> Collection:
		""" Returns the corresponding Pymongo Collection. """
		collection = cls.get_db()[cls.get_collection_name()]
		return collection

	@classmethod
	def get_db(cls) -> Database:
		""" NOTE: LogDocument overrides this in order to return a different mongo_db. """
		from .mongo_db import create_mongo_db
		return create_mongo_db()

	@classmethod
	def get_db_name(cls) -> str:
		""" Returns the name of the db we'll be using for this Document type. """
		return cls.get_db().name
	
	@classmethod
	def __class_query__(cls) -> dict:
		""" This method should return a dictionary that specifies a query which should always be applied when retrieving documents of this class. """
		# TODO: Extend this to also include subclasses of this type.
		return { __type_id__: cls.__type_id__ }
	
	@classmethod
	def __class_validation__(cls, document: Self) -> Self:
		""" This method should be run against all documents before any database operations are performed.
		Return the document as is if valid. Raise an error if invalid. """
		return document

	@classmethod
	def get_references(cls) -> dict[str, type["Document"]]:
		""" Returns the dictionary of foreign keys this Document stores as a dict of the field name -> referenced Document class. """
		from .. import type_registry
		document_info = next(iter(d for d in type_registry.document_info_list if d.cls is cls))
		return document_info.reference_fields

	# region: Document <> Bson
	# NOTE: When converting a Python Document into a mongo document, use to_document and from_document. These wrap obj_to_bson and bson_to_obj and are used by db_find_one() methods.
	# These bson_to_obj and obj_to_bson functions THEN access the to_bson and from_bson methods defined in BsonableDataclass. See readme.
	def to_document(self) -> dict[str, Any]:
		from ..typing.serialization.obj_to_bson import obj_to_bson
		
		# Before converting to document...
		# Validate that this object is still in a valid state
		self._validate_self()
		
		# Update the metadata for the document
		self.__last_modified__ = datetime.now().timestamp()
		
		# If you want to bring this back, probably put this into an env var
		# self.__last_modified_by_app_version__ = GLOBAL_VERSION

		document = obj_to_bson(self)

		# Suppress the serialization of __collection_name__
		if "__collection_name__" in document:
			del document["__collection_name__"]

		return document

	@classmethod
	def from_document(cls, document) -> Self:
		if not isinstance(document, dict):
			raise
		
		# Generate context
		collection_name = cls.get_collection_name()
		document_id = document.get("_id")
		if not document_id:
			raise
		last_modified_by_global_version = document.get("_last_modified_by_global_version_")
		last_modified_by_app_id = document.get("_last_modified_by_app_id_")
		context = DocumentContext(
			document_path=FieldPath.for_(cls),
			document_id=document_id,
			collection_name=collection_name,
			last_modified_by_global_version=last_modified_by_global_version,
			last_modified_by_app_id=last_modified_by_app_id
		)
		
		# Deserialize
		from ..typing.serialization.bson_to_type_annotation import bson_to_type_annotation
		obj = bson_to_type_annotation(document, cls, context)
		if not isinstance(obj, cls):
			raise ValueError(f"Expected document to be deserialized into {cls.__name__}. Instead, document was deserialized into {type(obj).__name__}")
		return obj
	# endregion

	def _validate_self(self) -> None:
		"""
		Force revalidation instance by rebuilding the instance.
		"""
		bson = self.to_bson()
		type(self).from_bson(bson, None)
	
	def __before_deleting__(self) -> bool:
		""" Override this if you want to add validation (like referential integrity) before deleting. """
		return True
	
	def __before_saving__(self, update_method: UpdateMethod) -> None:
		""" Extend this if you want to perform operations before saving. Useful for validation and for mirroring a new field into a legacy field. """
		# TODO: This needs to look at nested fields and run validation for those too
		
		# Run validation functions for each field
		for field_name, field_schema in type(self).__bsonable_fields__.items():
			if not isinstance(field_schema.schema_config, _DocumentSchemaConfig):
				continue
			
			field_value = getattr(self, field_name)
			
			# If we're saving before an insertion...
			if update_method is UpdateMethod.INSERT:
				# ...and the field has an insertion validation func
				if field_schema.schema_config.document_insertion_validation_func:
					# then run the insertion validation func, passing in self
					field_schema.schema_config.document_insertion_validation_func(self, field_value)
			
			# If we're saving before an update...
			elif update_method is UpdateMethod.UPDATE:
				# ...and the field has an update validation func
				if field_schema.schema_config.document_update_validation_func:
					# then run the update validation func, passing in the field pointer
					field_pointer = DocumentFieldPointer.for_(self._id, type(self), field_schema)
					field_schema.schema_config.document_update_validation_func(field_pointer, field_value)
		
	# Modification
	def replace(self, update: dict[str, Any]) -> Self:
		""" Return a copy of self with the specified fields replaced. """
		for key, value in update.items():
			if hasattr(self, key):
				setattr(self, key, value)
			else:
				raise AttributeError(f"{self.__class__.__name__} has no attribute '{key}'")
		
		self._validate_self()
		return self

	def anonymize(self) -> None:
		""" Assigns a new random id to itself. """
		self._id = DocumentId()

	# DB Class Methods
	@classmethod
	def db_insert_one(cls, document: 'Document') -> Self:
		""" """
		if not isinstance(document, Document):
			raise TypeError(f"Expected Document type, but got {type(document).__name__}")
		
		document.__before_saving__(UpdateMethod.INSERT)
		bson_doc = document.to_bson()
		result = cls.get_collection().insert_one(bson_doc)
		
		# Retrieve the inserted document to ensure we have the correct state
		inserted_doc = cls.db_require_one_by_id(result.inserted_id)
		return inserted_doc

	# Retrieval
	@classmethod
	def db_find_one(cls, query: dict | None = None) -> Self | None:
		""" Query the database and return the first matching document as a Python object. Returns None if there are no matching documents. """
		
		start_time = time.time()
		
		if query is None:
			query = {}
		
		document = cls.get_collection().find_one(cls.__class_query__() | query)
		
		print(f"Database Usage Logging: Retrieved document of type '{cls.__name__}' for query: {query} in {(time.time() - start_time):.3f} seconds")
		
		if not document:
			return None
		else:
			obj = cls.from_document(document)
			cls.__class_validation__(obj)
			return obj
		
	@classmethod
	def db_require_one(cls, query: dict | None = None) -> Self:
		""" Query the database and return the first matching document as a Python object. Raises an error if no matching document is found. """
		if query is None:
			query = {}
		obj = cls.db_find_one(query) # Includes validation
		if obj is None:
			raise ValueError(f"No document found for query: {query}")
		return obj # db_find_one already validates the object
	
	@classmethod
	def db_require_one_by_id(cls, _id: str) -> Self:
		""" Return one by id. Raises error if not found """
		query = { "_id": _id } # Assuming that _id is globally unique, we don't need to add the type query here
		document = cls.get_collection().find_one(query)
		if not document:
			raise ValueError(f"No {cls.__name__} found with _id {_id}.")
		else:
			obj = cls.from_document(document)
			if not isinstance(obj, cls): raise
			return cls.__class_validation__(obj)

	@classmethod
	def db_find_one_and_update(cls, filter: dict, update: dict, return_after_update: bool) -> Self | None:
		""" Find a single document and update it, returning either the original or the updated document. """

		return_option = ReturnDocument.AFTER if return_after_update else ReturnDocument.BEFORE

		document = cls.get_collection().find_one_and_update(
			filter=cls.__class_query__() | filter,
			update=update,
			return_document=return_option
		)

		if document:
			obj = cls.from_document(document)
			return cls.__class_validation__(obj)
		return None

	@classmethod
	def db_replace_one(cls, filter: dict, replacement: Self, upsert: bool = False) -> Self | None:
		""" Atomically replace a single document matching the filter with the replacement document.
		
		Args:
			filter: Query filter to match the document to replace
			replacement: The new document to replace the old one with
			upsert: If True, insert the document if no match is found. Defaults to False.
			
		Returns:
			The updated document if found and replaced (or inserted with upsert=True), None otherwise
		"""
		# Run before_saving hooks and validation
		replacement.__before_saving__(UpdateMethod.UPDATE)
		replacement = cls.__class_validation__(replacement)
		
		document = cls.get_collection().find_one_and_replace(
			filter=cls.__class_query__() | filter,
			replacement=replacement.to_document(),
			return_document=ReturnDocument.AFTER,
			upsert=upsert
		)

		if document:
			obj = cls.from_document(document)
			return cls.__class_validation__(obj)
		return None

	@classmethod
	def db_from_pipeline(cls, pipeline: _Pipeline) -> list[Self]:
		""" Returns a list of objs based on the pipeline. Note that the pipeline MUST produce bson that matches this class's expected bson format. """
		cursor = cls.get_collection().aggregate(pipeline)
		
		objs: list[Self] = []
		for document in cursor:
			obj = cls.from_document(document)
			objs.append(cls.__class_validation__(obj))
		return objs

	@classmethod
	def db_find_many(cls, query: dict, sort: dict | None = None, limit: int | None = None, skip: int | None = None) -> list[Self]:
		""" Query the database and return all matching documents as Python objects. """
		start_time = time.time()
		
		cursor = cls.get_collection().find(cls.__class_query__() | query)
		if sort:
			cursor = cursor.sort(sort)
		if limit:
			cursor = cursor.limit(limit)
		if skip:
			cursor.skip(skip)

		objs: list[Self] = []
		for document in cursor:
			obj = cls.from_document(document)
			objs.append(cls.__class_validation__(obj))
		
		print(f"Database Usage Logging: Retrieved {len(objs)} documents of type '{cls.__name__}' for query: {query} in {(time.time() - start_time):.3f} seconds")
		return objs

	@classmethod
	def db_count_documents(cls, query: dict) -> int:
		""" Return the total number of documents that match the query. """
		return cls.get_collection().count_documents(cls.__class_query__() | query)

	@classmethod
	def db_delete_one(cls, query: dict[str, Any]) -> None:
		""" Delete this object from the Mongo database. """
		# TODO: Instantiate an instance of this class and run __delete_validation__ first
		obj = cls.db_find_one(cls.__class_query__() | query) # Add class query to query
		if obj is None:
			raise ValueError("Error deleting the document. Are you sure a document matching this query exists?")
		obj.db_delete_self() # Includes validation
		
	@classmethod
	def db_delete_many(cls, query: dict[str, Any]) -> int:
		""" Delete all objects matching the query from the Mongo database. """		
		# TODO: Implement referential integrity checks
		# Delete all objects matching the query from the Mongo database
		result = cls.get_collection().delete_many(cls.__class_query__() | query) # Add class query to query
		return result.deleted_count

	@classmethod
	def db_insert_many(cls, objs: list[Self]) -> None:
		""" Insert multiple objects into the Mongo database. """
		if not objs:
			return
			
		documents = []
		for obj in objs:
			obj.__before_saving__(UpdateMethod.INSERT)
			document = cls.__class_validation__(obj).to_document()
			documents.append(document)
			
		cls.get_collection().insert_many(documents)

	# DB Instance Methods
	def db_insert_self(self) -> None:
		""" Insert this object into the Mongo database. 
		You may optionally specify an _id field.
		"""
		self.__before_saving__(UpdateMethod.INSERT)
		document = type(self).__class_validation__(self).to_document()
		type(self).get_collection().insert_one(document)

	def db_upsert_self(self) -> None:
		# Do not add __before_saving__ here, as db_insert and db_update should do that
		existing_obj = self.db_find_one({"_id": self._id}) # Assuming that _id's are globally unique, you don't need to add the type query here.
		if existing_obj is None:
			type(self).__class_validation__(self).db_insert_self()
		else:
			type(self).__class_validation__(self).db_update_self()

	def db_update_self(self) -> None:
		""" Persist the changes to the database. """
		start_time = time.time()
		
		# Validate before updating
		self.__before_saving__(UpdateMethod.UPDATE)
		# If this was a retrieved object, replace the existing db object with this one
		document = type(self).__class_validation__(self).to_document()
		result = type(self).get_collection().replace_one({"_id": self._id}, document) # type: ignore
		if result.matched_count != 1:
			raise ValueError(f"Error replacing the document. Are you sure a document with this _id {self._id} already exists?")
		
		print(f"Database Usage Logging: Updated document of type '{type(self).__name__}' with _id: {self._id} in {(time.time() - start_time):.3f} seconds")

	def db_delete_self(self) -> None:
		""" Delete this object from the Mongo database. """		
		if not self.__before_deleting__():
			raise ValueError("Can't delete this object because it is referenced by another.")
		
		result = type(self).get_collection().delete_one(type(self).__class_query__() | {"_id": self._id}) # type: ignore
		if result.deleted_count != 1:
			raise ValueError("Error deleting the document. Are you sure a document with this _id exists?")

	# Field updaters
	@overload
	def db_update_self_field(self, field_path: tuple[FieldSchema | Any, ...], new_value: Any) -> None:
		...
	
	@overload
	def db_update_self_field(self, field_path: FieldPath, new_value: Any) -> None:
		...

	def db_update_self_field(self, field_path: tuple[FieldSchema | Any, ...] | FieldPath, new_value: Any) -> None:
		""" Updates the specified field in the database and within the local Document obj. 
		Pass in a Python object for field value, NOT bson. """
		from ..typing.fields.field_pointer import DocumentFieldPointer
		
		# Run class validation on self
		self = type(self).__class_validation__(self)
		
		if isinstance(field_path, FieldPath):
			if field_path.containing_cls() is not type(self):
				raise ValueError("Inconsistent field path.")
		elif isinstance(field_path, tuple):
			field_path = FieldPath.for_(type(self), *field_path)
		else:
			raise ValueError
		
		# Validate that we can update this field
		field_schema = field_path.field_schema()
		if not isinstance(field_schema.schema_config, _DocumentSchemaConfig):
			raise ValueError(f"Field '{field_schema.field_name}' is not configured with DocumentFieldSchema. Attempted field access: {self}.")
		
		# Verify that this field is allowed to be edited directly
		if not field_schema.schema_config.allow_independent_update:
			raise ValueError(f"The field '{field_schema.field_name}' within class '{type(self).__name__}' is not indepdendently updateable.")
		
		# 1. Validate the field value against the field schema
		field_schema.type_expectation.validate(new_value, None)
		# 2. Run the dataclass field validation func, if defined
		if field_schema.schema_config.validation_func:
			field_schema.schema_config.validation_func(new_value)
		# 3. Run the document field validation func, if defined
		if field_schema.schema_config.document_update_validation_func:
			# Always pass in a pointer to the field itself, along with the new value. This way the document field validation function can lookup its own document if needed, and has context about its relationship to the document.
			field_schema.schema_config.document_update_validation_func(DocumentFieldPointer(self._id, field_path), new_value)
		
		# Conver to bson
		bson = obj_to_bson(new_value)

		# Get mongo field name (dot notation)
		mongo_field_name = field_path.as_mongo_db_dot_notation()

		updated_document = type(self).get_collection().find_one_and_update(
			{"_id": self._id},
			{
				"$set": { 
					mongo_field_name: bson, # Update the field value
					get_field_name(Document.__last_modified__): datetime.now().timestamp() # Update the document's __last_modified__
				},
				"$inc": { "__version__": 1 }, # Increment the document version
			},
			return_document=ReturnDocument.AFTER
		)
		
		# Update the document in memory
		if updated_document:
			updated_obj = type(self).from_document(updated_document)
			self.__dict__.update(updated_obj.__dict__)
		else:
			raise ValueError("Failed to update document. No matching document found or update operation failed.")

	@classmethod
	def db_update_field(cls, document_id: DocumentId, field_path: FieldPath, new_value: Any) -> None:
		""" Updates a single field in a document by its ID and field path. """
		from ..typing.fields.field_pointer import DocumentFieldPointer
		
		# Get the field schema
		field_schema = field_path.field_schema()
		if not isinstance(field_schema.schema_config, _DocumentSchemaConfig):
			raise ValueError(f"Field '{field_path}' is not configured to work within a Document. You should use DocumentSchemaConfig for fields you wish to use within Documents.")
		
		# Validate that we can update this field independently
		if not field_schema.schema_config.allow_independent_update:
			raise ValueError(f"Field '{field_path}' is not independently updateable.")

		# Validate the new value
		# 1. Validate type
		field_schema.type_expectation.validate(new_value, None)
		# 2. Run dataclass field validation, if defined
		if field_schema.schema_config.validation_func:
			field_schema.schema_config.validation_func(new_value)
		# 3. Run document field validation, if defined
		if field_schema.schema_config.document_update_validation_func:
			# Always pass in a pointer to the field itself, along with the new value. This way the document field validation function can lookup its own document if needed, and has context about its relationship to the document.
			field_schema.schema_config.document_update_validation_func(DocumentFieldPointer(document_id, field_path), new_value)
		
		# Convert to BSON
		bson = obj_to_bson(new_value)
		
		# Get mongo field name (dot notation)
		mongo_field_name = field_path.as_mongo_db_dot_notation()
		
		# Update the document
		updated_document = cls.get_collection().find_one_and_update(
			{"_id": document_id},
			{
				"$set": {
					mongo_field_name: bson,
					get_field_name(Document.__last_modified__): datetime.now().timestamp()
				},
				"$inc": {"__version__": 1}
			},
			return_document=ReturnDocument.AFTER
		)
		
		if not updated_document:
			raise ValueError(f"Failed to update document {document_id}. Document not found or update failed.")

	# Ownership
	def get_owner(self) -> DocumentId:
		""" Every Document should have a way to look up which user it belongs to. By default, this just looks for a field named fk_user_id. Override this if needed. """
		if not "fk_user_id" in type(self).__bsonable_fields__:
			raise NotImplementedError("Documents which don't have a fk_user_id field need to override this method to look up the user it belongs to.")
		fk_user_id = getattr(self, "fk_user_id")
		assert isinstance(fk_user_id, DocumentId)
		return fk_user_id
	
	@classmethod
	def db_get_documents_for_owner(cls, user_id: DocumentId) -> list[Self]:
		""" Returns all documents of this cls that belong to the specified user. """
		if not "fk_user_id" in cls.__bsonable_fields__:
			raise NotImplementedError(f"Document class {cls.__name__} must override this method as it does not have a field fk_user_id.")
		return cls.db_find_many({"fk_user_id": user_id})
	
	@classmethod
	def db_delete_documents_for_owner(cls, user_id: DocumentId) -> None:
		""" Deletes all documents of this cls that belong to the user. """
		if not "fk_user_id" in cls.__bsonable_fields__:
			raise NotImplementedError(f"Document class {cls.__name__} must override this method as it does not have a field fk_user_id.")
		logger.debug(f"Deleting documents of type '{cls.__name__}' for user '{user_id}'")
		cls.db_delete_many({"fk_user_id": user_id})

	# @classmethod
	# def __class_getitem__(cls, user_id: DocumentId) -> type['UserOwnedDocument']:
	# 	""" Provides a way to override the collection name. """
	# 	if not isinstance(user_id, DocumentId):
	# 		raise ValueError(f"user_id must be a DocumentId.")
		
	# 	class UserContextualizedDocumentCls(cls):
	# 		__skip_registration__ = True
	# 		__true_class__ = cls # Point to the true class for instance checks
	# 		__user_id__ = user_id
	# 		@property
	# 		def __class__(self):
	# 			""" Override __class__ so that when we type """
	# 			return type(self).__true_class__
	# 		@classmethod
	# 		def __class_query__(cls) -> dict:
	# 			# Filter by both __type_id__ and fk_user_id
	# 			base_query = {
	# 				__type_id__: cls.__type_id__,
	# 				"fk_user_id": cls.__user_id__
	# 			}
	# 			return base_query
	# 		@classmethod
	# 		def __class_validation__(cls, document: Self) -> Self:
	# 			if document.get_owner() != cls.__user_id__:
	# 				raise ValueError(f"Document does not match user id.")
	# 			return document
		
	# 	return UserContextualizedDocumentCls
	
	# @classmethod
	# def __class_query__(cls) -> dict:
	# 	raise ValueError(f"You must pass in UserRequiredDocument[user_id] when using user-required documents.")

	# @classmethod
	# def __class_validation__(cls) -> dict:
	# 	raise ValueError(f"UserRequiredDocuments must be used in the scope of a user.")