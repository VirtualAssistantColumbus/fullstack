## Consider deprecating or updating


How To:

    - Support legacy fields: override from_bson
    - Rename a collection: override get_collection_name:
    	@classmethod
        def get_collection_name(cls) -> str:
            #legacy: rename collection
            new_name = super().get_collection_name()
            old_name = "situation"
            # Fallback to the old name if the new name isn't there
            from .mongo_db import create_mongo_db
if not new_name in create_mongo_db().list_collection_names():
                print("Using old name")
                return old_name
            else:
                return new_name



NOTE: Documents implement Document.from_document and Document.to_document, which wrap bson_to_obj and obj_to_bson.
bson_to_obj and obj_to_bson then route to Document.from_bson and Document.to_bson within Document (which are inherited from BsonableDataclass).

This is accurately reflects what's happening.

The bson_to_obj and obj_to_bson methods are designed to route to the correct serialization functions for any bson or bsonable object.
When a Document is trying to serialize *itself* it must pass itself into bson_to_obj.