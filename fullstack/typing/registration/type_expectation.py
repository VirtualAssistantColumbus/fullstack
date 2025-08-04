from dataclasses import dataclass
from typing import Any

from .type_info import TypeInfo
from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from ...document.document_context import DocumentContext


@dataclass
class TypeExpectation:
	type_info: TypeInfo
	is_nullable: bool

	def __str__(self) -> str:
		output = self.type_info.type_.__name__
		if self.type_info.sub_type is not None:
			if isinstance(self.type_info.sub_type, type):
				output += f"[{self.type_info.sub_type.__name__}]"
			else:
				output += f"[{self.type_info.sub_type}]" # Handle FowardRefs
		if self.is_nullable:
			output += " | None"

		return output

	def validate(self, value: Any, document_context: 'DocumentContext | None'):
		""" Raises an error if the provided value does not match this TypeExpectation. """
		if not self._is_valid_value(value):
			raise ValueError(f"Value '{value}' is not valid according to this type expectation '{self}'.\n{document_context}")
	
	def _is_valid_value(self, value: Any):
		""" Validate that a value is consistent with this TypeExpectation. """
		if value is None:
			if self.is_nullable:
				return True
			else:
				return False
		
		#TODO: Also validate subtype!

		if not isinstance(value, self.type_info.type_):
			return False
		else:
			return True