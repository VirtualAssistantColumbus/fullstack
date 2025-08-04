# type: ignore

from typing import Any

from .field_schema import FieldSchema
from typing import TYPE_CHECKING

from ..registration.type_expectation import TypeExpectation
from ..registration.type_info import TypeInfo
if TYPE_CHECKING:
    from ..bsonable_dataclass.bsonable_dataclass import BsonableDataclass


class FieldPath(str):
    """ String representation of a path within a Bsonable structure. Pseudoprimitive. """

    def __new__(cls, path: str) -> 'FieldPath':
        """ You should not use this method directly. Instead, use .for_(). """
        return super().__new__(cls, path)

    def subfield(self, field_name: str) -> 'FieldPath':
        """ Returns a new DocumentPath obj which points to the specified dataclass subfield of the current document path. """
        return FieldPath(str(self) + "." + field_name)
    
    def subidx(self, idx: int) -> 'FieldPath':
        """ Returns a new DocumentPath obj which points to the specified index of an element of the current document path. """
        return FieldPath(str(self) + f"[{idx}]")
    
    def subkey(self, key: str) -> 'FieldPath':
        """ Returns a new DocumentPath obj which points to the specified dictionary key of the current document path. """
        escaped_key = self.escape_periods(str(key))
        return FieldPath(str(self) + f"{{{escaped_key}}}")

    def get_root_type_id(self) ->  str:
        return self.split(".")[0]

    def get_parts(self) -> tuple[str, ...]:
        parts = []
        current_part = ""
        i = 0
        while i < len(self):
            if self[i] == ".":
                if current_part:
                    parts.append(current_part)
                    current_part = ""
            elif self[i] == "[":
                if current_part:
                    parts.append(current_part)
                    current_part = ""
                # Find matching closing bracket
                j = i + 1
                while j < len(self) and self[j] != "]":
                    current_part += self[j]
                    j += 1
                parts.append(f"[{current_part}]")
                current_part = ""
                i = j
            elif self[i] == "{":
                if current_part:
                    parts.append(current_part)
                    current_part = ""
                # Find matching closing brace
                j = i + 1
                while j < len(self) and self[j] != "}":
                    current_part += self[j]
                    j += 1
                parts.append(f"{{{current_part}}}")
                current_part = ""
                i = j
            else:
                current_part += self[i]
            i += 1
        if current_part:
            parts.append(current_part)
        return tuple(parts[1:])  # Return all parts except for the root part
    
    def field_name(self) -> str:
        """ Return the field name of the field this path references. (i.e. the final field name) """
        return self.get_parts()[-1]

    def as_mongo_db_dot_notation(self) -> str:
        """ Returns the field path in MongoDB dot notation format, suitable for use in operations like $set.
        Handles both nested document fields and dictionary keys.
        
        Example:
            FieldPath("User.preferences{favorite.color}.value") -> "preferences.favorite|||color.value"
        """
        parts = self.get_parts()
        mongo_parts = []
        
        for part in parts:
            if part.startswith("{") and part.endswith("}"):
                # Convert dictionary key notation to dot notation, keeping periods escaped
                key = part[1:-1]  # Remove curly braces
                mongo_parts.append(key)  # The key is already escaped by subkey()
            elif part.startswith("[") and part.endswith("]"):
                # Convert array index notation
                mongo_parts.append(part[1:-1])  # Remove square brackets
            else:
                mongo_parts.append(part)
        
        return ".".join(mongo_parts)

    @staticmethod
    def for_(root_cls: type['BsonableDataclass'], *args: Any | FieldSchema) -> 'FieldPath':
        """ Creates a ClassFieldPointer. Pass in the containing document, followed by each field. """
        from ..bsonable_dataclass.bsonable_dataclass import BsonableDataclass
        from ..bsonable_dict.bsonable_dict import BsonableDict
        
        assert issubclass(root_cls, BsonableDataclass)
        field_path = FieldPath(root_cls.__type_id__)
        expected_container_cls = root_cls # Track what the previous containing class expected as the type for this child document_info
        for idx, field_schema in enumerate(args):
            if not isinstance(field_schema, FieldSchema):
                # If it's not a FieldSchema, check if we're dealing with a dictionary key
                if isinstance(expected_container_cls, type) and issubclass(expected_container_cls, BsonableDict):
                    # Validate the key type
                    if not isinstance(field_schema, expected_container_cls.__key__):
                        raise TypeError(f"Invalid dictionary key type. Expected {expected_container_cls.__key__.__name__}, got {type(field_schema).__name__}")
                    field_path = field_path.subkey(field_schema)
                    expected_container_cls = expected_container_cls.__value__.type_expectation.type_info.type_
                    continue
                raise ValueError(f"Cannot create field pointer for field '{field_schema}' of type '{type(field_schema).__name__}'. Field is not of type BsonableFieldInfo.")

            # Validate that this attribute actually exists in the immediate containing class
            if expected_container_cls is not field_schema.containing_cls:
                raise ValueError(f"Attempted to create FieldPath for invalid field sequence. Nested field '{field_schema.field_name}' belongs to '{field_schema.containing_cls}' which is not the expected containing class '{expected_container_cls.__name__}'. Is '{field_schema.field_name}' actually an attribute of '{expected_container_cls.__name__}'?")
            field_path = field_path.subfield(field_schema.field_name)
            expected_container_cls = field_schema.type_expectation.type_info.type_
        return field_path
    
    @staticmethod
    def escape_periods(field_name: str) -> str:
        """ Escapes periods in a field name by replacing them with |||.
        This allows field names containing periods to be used in dot notation paths. 
        
        We use our own syntax because replacing it with \u002E actually doesn't work (in browsers it converts to a period). """
        return field_name.replace(".", "|||")
    
    @staticmethod
    def unescape_periods(field_name: str) -> str:
        """ Unescapes periods in a field name by replacing ||| with periods.
        This reverses the escaping done by escape_periods(). """
        return field_name.replace("|||", ".")

    def extend(self, *args: Any | FieldSchema) -> 'FieldPath':
        """ Returns a new field path extended by the following args. """
        
        # The inital_cls will be the last member of the current (self) field path
        if self.get_parts():
            initial_cls = self.field_schema().type_expectation.type_info.type_
        else:
            initial_cls = self.containing_cls()
        
        # Extend the path
        field_path = self
        expected_container_cls = initial_cls # Track what the previous containing class expected as the type for this child document_info

        for idx, field_schema in enumerate(args):
            if not isinstance(field_schema, FieldSchema):
                raise ValueError(f"Cannot create field pointer for field '{field_schema}' of type '{type(field_schema).__name__}'. Field is not of type BsonableFieldInfo.")

            # Validate that this attribute actually exists in the immediate containing class
            if expected_container_cls is not field_schema.containing_cls:
                raise ValueError(f"Attempted to create FieldPath for invalid field sequence. Nested field '{field_schema.field_name}' belongs to '{field_schema.containing_cls}' which is not the expected containing class '{expected_container_cls.__name__}'. Is '{field_schema.field_name}' actually an attribute of '{expected_container_cls.__name__}'?")
            field_path = field_path.subfield(field_schema.field_name)
            expected_container_cls = field_schema.type_expectation.type_info.type_
        return field_path

    def containing_cls(self) -> type['BsonableDataclass']:
        from .. import type_registry
        
        type_id = self.get_root_type_id()
        containing_cls = type_registry.lookup_type_by_type_id(type_id)
        if containing_cls is None:
            raise ValueError(f"Error getting containing cls for FieldPath {self}. Does this field path specify a valid type id?")
        return containing_cls

    def field_schema(self) -> FieldSchema:
        """ Returns the FieldSchema for the field specified in this FieldPath. """
        from ..bsonable_dict.bsonable_dict import BsonableDict, __value__
        
        containing_cls = self.containing_cls()
        field_names = self.get_parts()

        for idx, field_name in enumerate(field_names):
            # Handle array index notation
            if field_name.startswith("[") and field_name.endswith("]"):
                # Handle lists later
                raise NotImplementedError
            
            # Handle dictionary key notation
            elif field_name.startswith("{") and field_name.endswith("}"):
                # Get the value type from the BsonableDict
                if not issubclass(containing_cls, BsonableDict):
                    raise TypeError(f"Type {containing_cls.__name__} is not a BsonableDict")
                
                # If this is the last element, return a FieldSchema for the dictionary value type
                if idx == len(field_names) - 1:
                    # The field schema for a dictionary value should come from the value_type class
                    if hasattr(containing_cls, __value__):
                        return getattr(containing_cls, __value__)
                    raise ValueError(f"Cannot get field schema for dictionary value type {containing_cls.__name__}")
                
                # If it's not the last element, update the containing class and then keep iterating
                containing_cls = containing_cls.__value__.type_expectation.type_info.type_  # Retrieve the value type in the value schema
                continue
            
            else:
                # Look up the attribute of the nested type from the type expectation
                if not hasattr(containing_cls, field_name):
                    raise AttributeError(f"'{containing_cls.__name__}' object has no attribute '{field_name}'")
                
                field_schema = getattr(containing_cls, field_name)
                if not isinstance(field_schema, FieldSchema):
                    raise ValueError(f"Field '{field_name}' is not a DocumentFieldInfo")
                
                # If last element
                if idx == len(field_names) - 1:
                    return field_schema
                
                # If it's not the last element, update the containing class and then keep iterating
                # Set the containing class to the type of the field's type expectation
                containing_cls = field_schema.type_expectation.type_info.type_

        raise RuntimeError("Unexpected code path reached while dereferencing pointer.")

    def navigate_into(self, instance: 'BsonableDataclass') -> Any:
        """ Returns the value at this field path within the given instance.
        For dataclasses, this gets the attribute value.
        For dictionaries, this gets the value at the key.
        
        Args:
            instance: The root instance to get the value from
            
        Returns:
            The value at this field path
        """
        from ..bsonable_dict.bsonable_dict import BsonableDict
        from ..serialization.bson_to_type_expectation import bson_to_type_expectation

        # Validate the root type matches
        if not isinstance(instance, self.containing_cls()):
            raise TypeError(f"Instance type {type(instance).__name__} does not match field path root type {self.containing_cls().__name__}")

        # Navigate through the parts to get the final value
        target = instance
        for part in self.get_parts():
            # Handle array index notation
            if part.startswith("[") and part.endswith("]"):
                if not hasattr(target, "__getitem__"):
                    raise TypeError(f"Cannot index into {type(target).__name__} using array notation '[{part}]'. Object is not subscriptable.")
                try:
                    idx = int(part[1:-1])
                except ValueError:
                    raise ValueError(f"Invalid array index '{part}'. Must be an integer.")
                if not (0 <= idx < len(target)):
                    raise IndexError(f"Array index {idx} is out of range for {type(target).__name__}")
                target = target[idx]
                continue

            # Handle dictionary key notation
            if part.startswith("{") and part.endswith("}"):
                if not isinstance(target, BsonableDict):
                    raise TypeError(f"Cannot access key in {type(target).__name__} using dictionary notation '{{{part}}}'. Object is not a BsonableDict.")
                key_str = self.unescape_periods(part[1:-1])

                # Deserialize the key from a string into the expected key type
                key_type_expectation = TypeExpectation(TypeInfo(target.__key__, None), False)
                key = bson_to_type_expectation(key_str, key_type_expectation, None, coerce_str_values=True)

                # Lookup the key in the dict
                if not isinstance(key, target.__key__):
                    raise TypeError(f"Dictionary key '{key}' is of type {type(key).__name__}, but {type(target).__name__} expects keys of type {target.__key__.__name__}")
                if key not in target:
                    raise KeyError(f"Dictionary key '{key}' not found in {type(target).__name__}")
                target = target[key]
                continue

            # Handle regular attribute access
            if not hasattr(target, part):
                raise AttributeError(f"'{type(target).__name__}' object has no attribute '{part}'")
            target = getattr(target, part)

        return target

    def update_instance(self, instance: 'BsonableDataclass', new_value: Any) -> None:
        """ Updates the instance at this field path with the new value.
        For dataclasses, this sets the attribute.
        For dictionaries, this updates the key-value pair.
        
        Args:
            instance: The root instance to update
            new_value: The new value to set at this field path
        """
        from ..bsonable_dataclass.bsonable_dataclass import BsonableDataclass
        from ..bsonable_dict.bsonable_dict import BsonableDict
        
        # Validate the root type matches
        if not isinstance(instance, self.containing_cls()):
            raise TypeError(f"Instance type {type(instance).__name__} does not match field path root type {self.containing_cls().__name__}")
        
        # Navigate to the parent instance and keep track of the final part
        target: BsonableDataclass | BsonableDict = instance
        parts = self.get_parts()
        
        # If only one part, we're updating the root instance directly
        if len(parts) == 1:
            final_part = parts[0]
            parent = target
        else:
            # Navigate to the parent of the target
            for part in parts[:-1]:
                # Handle array index notation
                if part.startswith("[") and part.endswith("]"):
                    if not hasattr(target, "__getitem__"):
                        raise TypeError(f"Cannot index into {type(target).__name__} using array notation '[{part}]'. Object is not subscriptable.")
                    try:
                        idx = int(part[1:-1])
                    except ValueError:
                        raise ValueError(f"Invalid array index '{part}'. Must be an integer.")
                    if not (0 <= idx < len(target)):
                        raise IndexError(f"Array index {idx} is out of range for {type(target).__name__}")
                    target = target[idx]
                    continue
                
                # Handle dictionary key notation
                if part.startswith("{") and part.endswith("}"): 
                    if not isinstance(target, BsonableDict):
                        raise TypeError(f"Cannot access key in {type(target).__name__} using dictionary notation '{{{part}}}'. Object is not a BsonableDict.")
                    key = self.unescape_periods(part[1:-1])
                    if not isinstance(key, target.__key__):
                        raise TypeError(f"Dictionary key '{key}' is of type {type(key).__name__}, but {type(target).__name__} expects keys of type {target.__key__.__name__}")
                    if key not in target:
                        raise KeyError(f"Dictionary key '{key}' not found in {type(target).__name__}")
                    target = target[key]
                    continue
                
                # Handle regular field access
                if not hasattr(target, part):
                    raise AttributeError(f"'{type(target).__name__}' has no attribute '{part}'")
                target = getattr(target, part)
                continue
            
            parent = target
            final_part = parts[-1]
        
        # Update the value based on the parent type and final part
        if final_part.startswith("{") and final_part.endswith("}"): 
            # Dictionary update
            if not isinstance(parent, BsonableDict):
                raise TypeError(f"Cannot update key in {type(parent).__name__} using dictionary notation '{{{final_part}}}'. Object is not a BsonableDict.")
            key = self.unescape_periods(final_part[1:-1])
            if not isinstance(key, parent.__key__):
                raise TypeError(f"Dictionary key '{key}' is of type {type(key).__name__}, but {type(parent).__name__} expects keys of type {parent.__key__.__name__}")
            # Validate value type against dictionary's value type
            if not isinstance(new_value, parent.__value__):
                raise TypeError(f"New value type '{type(new_value).__name__}' does not match dictionary value type '{parent.__value__.__name__}'")
            parent[key] = new_value
        elif final_part.startswith("[") and final_part.endswith("]"):
            # List update
            if not hasattr(parent, "__setitem__"):
                raise TypeError(f"Cannot update index in {type(parent).__name__} using array notation '[{final_part}]'. Object is not subscriptable.")
            try:
                idx = int(final_part[1:-1])
            except ValueError:
                raise ValueError(f"Invalid array index '{final_part}'. Must be an integer.")
            if not (0 <= idx < len(parent)):
                raise IndexError(f"Array index {idx} is out of range for {type(parent).__name__}")
            parent[idx] = new_value
        else:
            # Dataclass attribute update
            if not hasattr(parent, final_part):
                raise AttributeError(f"'{type(parent).__name__}' has no attribute '{final_part}'")
            # Get the field schema directly from the parent class
            field_schema = getattr(type(parent), final_part)
            assert isinstance(field_schema, FieldSchema)
            if not field_schema.type_expectation.validate(new_value, None):
                actual_type = type(new_value).__name__
                expected_type = field_schema.type_expectation.type_info.type_.__name__
                raise TypeError(f"New value type '{actual_type}' does not match field type expectation '{expected_type}' for field '{field_schema.field_name}'")
            setattr(parent, final_part, new_value)