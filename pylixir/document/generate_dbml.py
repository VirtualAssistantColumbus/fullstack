from ..typing.registration.type_registry import TypeRegistry
from ..typing import type_registry
from ..typing.registration.type_expectation import TypeExpectation


def type_expectation_to_dbml(type_expectation: TypeExpectation):
    """ Tries to reconstruct the type annotation. """
    output = type_expectation.type_info.type_.__name__
    if type_expectation.type_info.sub_type:
        output = output + f"({type_expectation.type_info.sub_type.__name__})" #type: ignore
    # if not self.is_nullable:
    # 	output = output + " [not null]"
    return output

def generate_dbml(mongoable_type_registry: TypeRegistry, *, keys_only: bool = True, suppress_fk_user_id: bool = True) -> str:
    """ A utility to generate the schema code you can use in dbdiagram.io straight from the actual Document type definitions. """
    
    lines = []
    indent_level = 0
    
    def add_line(text: str = ""):
        if text:
            lines.append("\t" * indent_level + text)
        else:
            lines.append("")
    
    def add_double_spaced_line(text: str):
        if lines:  # If not empty, add a blank line first
            lines.append("")
        add_line(text)
    
    def delete_last_line():
        if lines:
            lines.pop()
    
    for document_info in mongoable_type_registry.document_info_list:
        
        # Use the collection name for the Table name (not the Document class name)
        add_double_spaced_line(f"Table {document_info.collection_name} {{")
        indent_level += 1

        # Add non reference fields
        if not keys_only:
            all_fields = document_info.cls.__bsonable_fields__
            all_field_names = all_fields.keys()
            reference_field_names = document_info.reference_fields.keys()
            non_reference_field_names = all_field_names - reference_field_names
            for non_reference_field_name in non_reference_field_names:
                type_expectation = all_fields[non_reference_field_name].type_expectation
                field_dbml = type_expectation_to_dbml(type_expectation)
                add_line(f"{non_reference_field_name} {field_dbml}")
        else:
            # Just add the ._id field so we have a primary key to reference
            add_line("_id DocumentId [primary key]")
        
        # Add reference fields
        for reference_field_name, referenced_document_cls in document_info.reference_fields.items():
            add_line(f"{reference_field_name} ForeignKey [ref: > {referenced_document_cls.__collection_name__}._id]") # Mark them all as ForeignKeys
            if reference_field_name == "fk_user_id" and suppress_fk_user_id:
                if suppress_fk_user_id:
                    delete_last_line()
                    add_line(f"{reference_field_name} ForeignKey")
        
        indent_level -= 1
        add_line("}")
    
    return "\n".join(lines)


dbml = generate_dbml(type_registry)
print(dbml)