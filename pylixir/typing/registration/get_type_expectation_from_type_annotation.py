from types import UnionType

from .get_type_info import get_type_info_list
from .type_expectation import TypeExpectation


def get_type_expectation_from_type_annotation(type_annotation: type | UnionType, *, resolve_forward_refs: bool = False) -> TypeExpectation:
	"""	### Interpret based on type annotations, including nullable types and types with sub-types. ###
	From the annotation, get a list of types
	
	NOTE: Resolve forward refs cannot be used in a context where we haven't yet registered our types. (i.e. not at the class definition level.)
	"""

	expected_type_info_list = list(get_type_info_list(type_annotation))
	
	is_nullable = False
	
	# If there's only one type option, the expected_type should be that option
	if len(expected_type_info_list) == 1:
		expected_type_info = expected_type_info_list[0]
	
	# If there's two type options, check to make sure the Union type is just a nullable type
	elif len(expected_type_info_list) == 2:
		for idx, type_info in enumerate(expected_type_info_list):
			if type_info.type_ is type(None):
				is_nullable = True
				# Remove None as an option and note the remaining type
				expected_type_info_list.pop(idx)
				expected_type_info = expected_type_info_list[0]
		if not is_nullable:
			raise ValueError("The only reason we should have multiple annotated types is if one is None.")
	
	# We can't handle union types with three types.
	else:
		raise NotImplementedError("We don't handle annotations with more than two types.")
	
	return TypeExpectation(
		type_info=expected_type_info,
		is_nullable=is_nullable
	)