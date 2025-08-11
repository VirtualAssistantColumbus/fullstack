import re

from ...utilities.validation_error import ValidationError


class SafeStr(str):
    """ String class that automatically HTML escapes when rendered. Used in Document fields for safe HTML display. """
    def __new__(cls, value):
        cls._validate(value)
        return super().__new__(cls, value)

    # # We don't need to escape on output, because SafeStr must be safe when instantiated.
    # def __format__(self, format_spec):
    #     return format(html.escape(self), format_spec)

    # def __str__(self):
    #     return html.escape(self)

    @staticmethod
    def _validate(value):
        if not isinstance(value, str):
            raise ValueError("SafeStr can only be created from strings.")

        # Check for HTML or script indicators
        if re.search(r'<[^>]+>', value):
            raise ValidationError("Input contains HTML-like tags and is not allowed.")

        if re.search(r'(?i)javascript:', value):
            raise ValidationError("Input contains potentially dangerous content (e.g., javascript:).")