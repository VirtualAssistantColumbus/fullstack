ABSTRACT = "ABSTRACT"
""" 
This keyword is used for:
    - Documents (__collection_name__)
    - BsonableDataclasses (__type_id__)
    - Pages (__page_path__)

To indicate an item that does not need to be registered.
"""

AUTO = "AUTO_1234"
"""
This is used: 
    - With BsonableDataclasses, to assign a __type_id__ based on the class name. (This should not be used for Documents, as we want to have stable type ids in the database.)
    - With SingletonElements, to assign a __div_id__ based on the class name.
"""

FROM_CLASS = "FROM_CLASS"
""" Designates that this parameter will be assigned by the class. """


INHERIT = "INHERIT"
"""
This keyword is used to indicate that an attribute should be inheritted from the parent class.
"""