from typing import Any, Union

from ...typing.fields.field_path import FieldPath


def unflatten(**kwargs: str) -> dict[str, Any]:
    """
    Constructs a nested json object from flat dot notation values, supporting both dictionaries and lists.
    
    Args:
        **kwargs: Key-value pairs where keys are dot-separated strings representing nested structure.
                 List indices are denoted with square brackets, e.g., "field[0]".
    """
    # Sort kwargs to ensure consistent processing order
    sorted_kwargs: list[tuple[str, str]] = sorted(kwargs.items())

    def parse_part(part: str) -> tuple[str, Union[int, None]]:
        """Parse a path part into field name and optional array index."""
        if '[' in part and part.endswith(']'):
            field_name, idx_str = part.split('[', 1)
            try:
                index = int(idx_str[:-1])  # Remove the closing bracket
                if index < 0:
                    raise ValueError(f"Negative index not allowed: {index}")
                return field_name, index
            except ValueError as e:
                raise ValueError(f"Invalid array index in '{part}'") from e
        return part, None

    def build_intermediate_dict(items: list[tuple[str, str]]) -> dict[str, Any]:
        """
        Build intermediate dictionary structure where everything is a dict,
        with special __type__ markers to indicate true dicts vs lists.
        """
        result: dict[str, Any] = {"__type__": "dict"}
        
        for key, value in items:
            parts = [FieldPath.unescape_periods(p) for p in key.split('.')]
            if '' in parts:
                raise ValueError(
                    f"Invalid key format: '{key}'. Keys should not contain consecutive dots or start/end with a dot."
                )
            
            current = result
            # Process all parts except the last one
            for part in parts[:-1]:
                field_name, index = parse_part(part)
                
                # If this is the first time we're seeing this field
                if field_name not in current:
                    # If it has an index, it should be a list-type dict
                    if index is not None:
                        current[field_name] = {"__type__": "list"}
                    else:
                        current[field_name] = {"__type__": "dict"}
                
                # Move to the next level
                next_container = current[field_name]
                if index is not None:
                    # For list-type dicts, we store indices as string keys
                    str_idx = str(index)
                    if str_idx not in next_container:
                        next_container[str_idx] = {"__type__": "dict"}
                    current = next_container[str_idx]
                else:
                    current = next_container
            
            # Handle the final part
            last_field, last_index = parse_part(parts[-1])
            
            if last_index is not None:
                # If this is a list item
                if last_field not in current:
                    current[last_field] = {"__type__": "list"}
                str_idx = str(last_index)
                current[last_field][str_idx] = value
            else:
                # If this is a regular field
                current[last_field] = value
        
        return result

    def convert_intermediate_to_final(data: Any) -> Any:
        """
        Recursively convert the intermediate structure to the final form,
        transforming list-type dicts into actual lists without gaps.
        """
        # If this isn't a dict or doesn't have __type__, return as is
        if not isinstance(data, dict) or "__type__" not in data:
            return data
        
        # Remove the type marker
        data_type = data.pop("__type__")
        
        if data_type == "list":
            # Convert dict with string indices to list
            # First, convert all values recursively
            converted_dict = {k: convert_intermediate_to_final(v) for k, v in data.items()}
            
            if not converted_dict:
                return []
            
            # Sort by numeric index and create a compact list
            sorted_items = sorted(converted_dict.items(), key=lambda x: int(x[0]))
            return [value for _, value in sorted_items]
        
        else:  # data_type == "dict"
            # Recursively convert all values
            return {k: convert_intermediate_to_final(v) for k, v in data.items()}

    try:
        # Build the intermediate structure
        intermediate = build_intermediate_dict(sorted_kwargs)
        # Convert to final form
        return convert_intermediate_to_final(intermediate)
    except Exception as e:
        # Catch any unexpected exceptions and provide a helpful message
        raise ValueError(f"Error processing input: {str(e)}") from e

# data = {
#     "items[0].name": "First",
#     "items[0].value": "100",
#     "items[1].name": "Second",
#     "items[1].tags[0]": "tag1",
#     "items[1].tags[1]": "tag2"
# }
# result = unflatten(**data)
# print(result)

# test_data: dict[str, str] = {
#     "root": "1",
# 	"root.one": "1",
#     "root.two": "2",
#     "root.nested.three": "3",
#     "root.nested.four": "4",
#     "another.five": "5"
# }

# # test_data = {
# # 	"root.one": "1",
# # 	"root.two": "2",
# # }

# json = form_to_json(**test_data)

# print(json)