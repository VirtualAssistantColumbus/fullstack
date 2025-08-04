from abc import ABCMeta
from typing import Any, ClassVar, dataclass_transform, get_origin
import warnings

from ..fields.schema_config import DocumentSchemaConfig, SchemaConfig, _SchemaConfig
from ..fields.field_schema import FieldSchema
from ...utilities.special_values import AUTO
from ...utilities.undefined import UNDEFINED
from ..serialization.vars import __type_id__, __true_class__


__bsonable_fields__ = "__bsonable_fields__"
__frozen__ = "__frozen__"

# Fields with double underscores will not be included in __bsonable_fields__
# __bsonable_fields__
# __path_prefix__
# __login_required__
# __type_id__
# __frozen__

# Include these fields even though they have double underscores
INCLUDE_SPECIAL_FIELDS = [
	"__version__",
	"__last_modified__"
]

__initialized__ = "__initialized__"

SPECIAL_INSTANCE_FIELDS = (
	__initialized__,
)

# TODO: We should allow BsonableDataclasses to also use DocumentSchemaConfig and access the allow_independent_update

@dataclass_transform(field_specifiers=(SchemaConfig, DocumentSchemaConfig), kw_only_default=False)
class BsonableDataclassMeta(ABCMeta):
	"""Metaclass for BsonableDataclass that handles field registration and validation.
	
	This metaclass processes fields using either SchemaConfig or DocumentSchemaConfig through 
	the same mechanism. When a field is defined with DocumentSchemaConfig, it gains additional 
	document validation functionality since _DocumentSchemaConfig inherits from _SchemaConfig.

	BsonableDataclasses can use DocumentSchemaConfig even though they aren't documents themselves,
	as they may be used as fields within Documents and thus need to support document-specific 
	features like pointer-based updates.

	Example usage:
		class MyDataclass(BsonableDataclass):
			# Regular field with basic schema config
			field1: str = SchemaConfig(default="example")
			
			# Field with document validation capabilities
			field2: str = DocumentSchemaConfig(
				default="example",
				allow_independent_update=True
			)

	The metaclass will:
	1. Create FieldSchema instances for each annotated field
	2. Store the schema config (either SchemaConfig or DocumentSchemaConfig) within the FieldSchema
	3. Store the FieldSchema within both the class field and the class's __bsonable_fields__ dictionary
	4. Handle inheritance of fields from parent classes
	5. Manage frozen state and initialization
	"""

	def __subclasscheck__(cls, subclass: type) -> bool:
		if hasattr(cls, __true_class__):
			true_cls = getattr(cls, __true_class__)
			return true_cls.__subclasscheck__(subclass)
		return type.__subclasscheck__(cls, subclass)

	def __new__(cls, name, bases, dct, *, frozen: bool = False):
		from ..registration.get_type_expectation_from_type_annotation import get_type_expectation_from_type_annotation
		
		# Create the new class
		new_cls = super().__new__(cls, name, bases, dct)
		
		# Handle AUTO type_id before anything else
		if hasattr(new_cls, '__type_id__') and getattr(new_cls, '__type_id__') == AUTO:
			setattr(new_cls, '__type_id__', name)
		
		# Initialize the __bsonable_fields__ dictionary
		setattr(new_cls, __bsonable_fields__, {})

		# Collect fields from base classes
		for base in bases:
			if hasattr(base, __bsonable_fields__):
				new_cls.__bsonable_fields__.update(base.__bsonable_fields__) #type: ignore

		# For each annotated field, create a FieldSchema and store it within cls.__bsonable_fields__ as well as the class field itself.
		# 1/2/2025 Update: Updated this to also include annotations on parent classes. This is so that the field schema will show the containing_cls as *this* subclass, not the parent class. (So Document _ids will show the containing class as the Document type, not Document)
		# Collect all annotations, including those from parent classes
		annotations_dict = {}
		for base in bases:
			if hasattr(base, '__annotations__'):
				annotations_dict.update(base.__annotations__)
		annotations_dict.update(dct.get('__annotations__', {}))
		
		for field_name, field_annotation in annotations_dict.items():
			# UPDATE: Skip processing any fields surrounded by double underscores, except for specially designated ones.
			assert isinstance(field_name, str)
			if (field_name.startswith("__") and field_name.endswith("__")
	   			and field_name not in INCLUDE_SPECIAL_FIELDS):
				continue
			
			# Skip class variables
			if get_origin(field_annotation) is ClassVar:
				continue

			# Get the type expectation for the field
			type_expectation = get_type_expectation_from_type_annotation(field_annotation)

			# Check if the field is annotated as str and warn about using SafeStr instead
			if type_expectation.type_info.type_ is str:
				warning_msg = (
					f"Field '{field_name}' in class '{name}' is annotated as 'str'. "
					"Consider using 'SafeStr' from type_registration.safe_str instead for automatic HTML escaping."
				)
				warnings.warn(warning_msg, UserWarning)
			
			# Determine the field configuration
			field_config = SchemaConfig()
			
			# 1/2/2025 Update: Modified this to also include attributes defined on parent classes
			# cls_field_value = new_cls.__dict__.get(field_name, UNDEFINED) # Access __dict__ directly to get cls attributes defined on the class, and not any parent classes.
			cls_field_value = getattr(new_cls, field_name, UNDEFINED) # Use getattr to get cls attributes defined on the class and parent classes.
			
			if cls_field_value is not UNDEFINED:
				# 1/10/2025 Update: Allowed field from parent classes to be registered
				
				# If the cls field stores a FieldConfig, use this as the FieldConfig.
				# A subclass which defines its own _SchemaConfig will override the parent class's settings for this field
				if isinstance(cls_field_value, _SchemaConfig):
					field_config = cls_field_value
				
				# Fields from parent classes will have already been converted to FieldSchema objects. So, we should pull out the SchemaConfig from these.
				elif isinstance(cls_field_value, FieldSchema):
					field_config = cls_field_value.schema_config
				
				# End update
				
				# Otherwise, create a FieldConfig which specifies a default value of the provided value
				else:
					field_config = SchemaConfig(
						default=cls_field_value
					)

			# Validate that any default values conform to the type annotation
			if field_config.has_default():
				if not type_expectation._is_valid_value(field_config.get_default()):
					raise ValueError(f"Field '{field_name}' has an improperly set default value. Expected type '{type_expectation}' but specified default value of {field_config.get_default()}.")

			# Generate the FieldSchema for the field
			field_schema = FieldSchema(
				field_name=field_name,
				containing_cls=new_cls, #type: ignore
				type_expectation=type_expectation,
				configuration=field_config
			)
			
			# Store the FieldSchema into both cls.__bsonable_fields__ as well as the cls field itself
			setattr(new_cls, field_name, field_schema)
			new_cls.__bsonable_fields__[field_name] = field_schema #type: ignore
		
		# Set the frozen attribute based on the kwarg passed into the class
		setattr(new_cls, __frozen__, frozen)

		# Define the __init__ method
		def __init__(self, *args, **kwargs):
			from .bsonable_dataclass import BsonableDataclass
			if not isinstance(self, BsonableDataclass): raise

			# Separate out kwonly fields
			positional_or_kw_fields: dict[str, FieldSchema] = {}
			kw_only_fields: dict[str, FieldSchema] = {}
			for field_name, field_schema in type(self).__bsonable_fields__.items():
				if field_schema.schema_config.kw_only:
					kw_only_fields.update({field_name: field_schema})
				else:
					positional_or_kw_fields.update({field_name: field_schema})

			# Track positional args by storing them into a dict
			args_dict: dict[int, Any] = dict(enumerate(args))

			# Handle positional or kwonly args
			# Attempt to assign a value using either a positional arg, a kwarg, or a default value
			for idx, (field_name, field_schema) in enumerate(positional_or_kw_fields.items()):
				# Assign the positional arguments to the field, if there are any that line up with the idx
				if idx in args_dict:
					field_value = args_dict.pop(idx)
				# Otherwise, look for it in kwargs
				elif field_name in kwargs:
					field_value = kwargs.pop(field_name) # Retrieve and remove the kwarg from kwargs
				# Finally, see if there is a default value.
				elif field_schema.schema_config.has_default():
					field_value = field_schema.schema_config.get_default()
				else:
					raise ValueError(f"Error creating instance of '{type(self).__name__}'. Field '{field_name}' was not supplied.")
				
				# Validate the field value
				field_schema.validate_field_value(field_value)
				
				# Stash into object
				setattr(self, field_name, field_value)
			
			# If we have leftover args, raise an error
			if len(args_dict):
				extra_args_str = ", ".join(f"Idx {idx}: Value '{value}'" for idx, value in args_dict.items())
				raise ValueError(f"Error creating instance of '{type(self).__name__}'. Too many positional arguments were supplied. The following positional arguments do not line up with the defined fields. { extra_args_str }")

			# Handle kwonly fields
			for field_name, field_schema in kw_only_fields.items():
				# Look for it in kwargs
				if field_name in kwargs:
					field_value = kwargs.pop(field_name) # Retrieve and remove the kwarg from kwargs
				# Or see if there is a default value.
				elif field_schema.schema_config.has_default():
					field_value = field_schema.schema_config.get_default()
				else:
					raise ValueError(f"Error creating instance of '{type(self).__name__}'. Required keyword-only field '{field_name}' was not supplied.")

				# Validate the field value
				field_schema.validate_field_value(field_value)

				# Stash into object
				setattr(self, field_name, field_value)

			# Store extra kwargs into the obj
			for extra_field_name, extra_field_value in kwargs.items():
				setattr(self, extra_field_name, extra_field_value)

			# Mark the instance as initialized (this is used to enforce the 'frozen' keyword.)
			setattr(self, __initialized__, True)

			# If this class defines a __post_init__ method, run it.
			self.__post_init__()

		def __setattr__(self, field_name, field_value):
			if getattr(self, "__initialized__", False) and getattr(type(self), '__frozen__', False):
				raise AttributeError(f"Failed to update field '{field_name}' to value '{field_value}'. Frozen dataclass of type '{type(self).__name__}' cannot be modified.")

			# TODO: Validate when updating attributes? That might actually be computationally expensive. Probably better to just validate when applying pointer updates and when updating documents.

			super(new_cls, self).__setattr__(field_name, field_value)
		
		# Set the __init__ method to the new class
		new_cls.__init__ = __init__
		new_cls.__setattr__ = __setattr__ #type: ignore # NOTE
		
		return new_cls