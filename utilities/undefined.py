class Undefined:
    """ Utilize this singleton when you need to disambiguate between a field which is set as None vs. a field which has not been set at all. 
    NOTE: This is currently used in:
        - BsonableDataclassMeta
        - BsonableDataclass's SchemaConfig() function
        - HtmlAttr
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "BsonableUndefined"

    def __bool__(self):
        return False

UNDEFINED = Undefined()