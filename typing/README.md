# Type Registration Module

A reusable Python module for automatic type registration and serialization of custom dataclasses and primitives. This module provides a centralized type registry that can be configured for any project.

## Overview

The `type_registration` module provides:
- **Automatic type discovery** via introspection of imported classes
- **Configurable pseudo-primitives** for custom serialization types
- **Pluggable serialization functions** for custom serialization logic
- **Type-safe registry** for runtime type lookups and validation
- **Project-agnostic design** - can be dropped into any Python project

## Prerequisites

Before using this module, you must set the following environment variables:

```bash
# Required for MongoDB connection
export MONGO_URL="mongodb://localhost:27017"  # Your MongoDB connection string
export MONGO_DB_NAME="your_database_name"     # Your database name

# Optional for separate log database
export MONGO_LOG_DB_NAME="your_log_database_name"  # Separate database for logging documents (defaults to main database)
```

The module will automatically create database connections using these environment variables when needed.

## Quick Start

### 1. Create a Type Preparation File

Create a `type_preparation.py` file in your project root (or any location) that imports your types and configures the module:

```python
"""
Type Preparation for MyProject

This file imports all types that need to be registered and configures
the type_registration module for this project.
"""

import type_registration

# ===== IMPORT YOUR TYPES =====
# Import all BsonableDataclass types to make them discoverable
from myproject.models.user import User
from myproject.models.order import Order
from myproject.models.product import Product

# Import your custom pseudo-primitive types
from myproject.types.custom_date import CustomDate
from myproject.types.money import Money
from myproject.types.email import Email

# ===== CONFIGURE PSEUDO-PRIMITIVES =====
# Add your custom pseudo-primitives to the module
type_registration.pseudo_primitives.extend([
    # Built-in types
    list, tuple, set, frozenset,
    
    # Your custom types
    CustomDate, Money, Email,
    
    # Standard library types you want to treat as pseudo-primitives
    datetime, date, time, timedelta
])

# ===== CONFIGURE SERIALIZATION FUNCTIONS =====
# Define your custom serialization functions
def my_pseudo_primitive_to_bson(obj):
    """Convert pseudo-primitive objects to BSON-compatible format."""
    if isinstance(obj, CustomDate):
        return {"type": "CustomDate", "value": obj.to_iso_string()}
    elif isinstance(obj, Money):
        return {"type": "Money", "amount": obj.amount, "currency": obj.currency}
    elif isinstance(obj, Email):
        return {"type": "Email", "address": str(obj)}
    else:
        # Handle built-in types
        return str(obj)

def my_bson_to_pseudo_primitive(bson, expected_type_info, document_context=None, *, coerce_str_values=False):
    """Convert BSON back to pseudo-primitive objects."""
    if isinstance(bson, dict) and "type" in bson:
        if bson["type"] == "CustomDate":
            return CustomDate.from_iso_string(bson["value"])
        elif bson["type"] == "Money":
            return Money(bson["amount"], bson["currency"])
        elif bson["type"] == "Email":
            return Email(bson["address"])
    
    # Handle built-in types
    expected_type = expected_type_info.type_
    if expected_type == list:
        return list(bson)
    elif expected_type == tuple:
        return tuple(bson)
    # ... handle other types
    
    return bson

# Set the custom serialization functions
type_registration.pseudo_primitive_to_bson.set_function(my_pseudo_primitive_to_bson)
type_registration.bson_to_pseudo_primitive.set_function(my_bson_to_pseudo_primitive)

# ===== REGISTER EVERYTHING =====
# This populates the type registry with all imported types
type_registration.create_type_registry()

# ===== READY TO USE =====
# Now type_registration.type_registry is fully configured and ready!
print("✅ Type registration complete!")
```

### 2. Import Your Type Preparation File

In your application startup code, simply import your type preparation file:

```python
# In your main.py or app startup
import type_preparation  # This configures everything

# Now you can use the type registry
from type_registration import type_registry

# Use the registry for type lookups
user_type = type_registry.lookup_type_by_type_id("User")
is_primitive = type_registry.is_primitive_cls(str)
```

## Detailed Configuration Guide

### BsonableDataclass Types

Any class that inherits from `BsonableDataclass` will be automatically discovered and registered when imported. Make sure to:

1. **Import the classes** in your type preparation file
2. **Define `__type_id__`** in each class:

```python
from type_registration.bsonable_dataclass.bsonable_dataclass import BsonableDataclass

class User(BsonableDataclass):
    __type_id__ = "User"  # Must be unique across your project
    
    name: str
    email: str
    age: int
```

### Pseudo-Primitives

Pseudo-primitives are types that need custom serialization but aren't full BsonableDataclasses. Common examples:

```python
# Add to type_registration.pseudo_primitives
type_registration.pseudo_primitives.extend([
    # Built-in Python types
    datetime, date, time, timedelta, UUID,
    list, tuple, set, frozenset,
    
    # Your custom value types
    Money, Email, PhoneNumber, CustomDate,
    
    # Third-party types
    numpy.ndarray, pandas.DataFrame,
])
```

### Serialization Functions

#### SerializationFunc - pseudo_primitive_to_bson

**Signature**: `(obj: Any) -> Any`

```python
def my_serializer(obj):
    """Convert pseudo-primitive to BSON-compatible format."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, Money):
        return {"amount": obj.amount, "currency": obj.currency}
    elif isinstance(obj, list):
        return [serialize_item(item) for item in obj]
    # ... handle other types
    return str(obj)

type_registration.pseudo_primitive_to_bson.set_function(my_serializer)
```

#### DeserializationFunc - bson_to_pseudo_primitive

**Signature**: `(bson: Any, expected_type_info: TypeInfo, document_context: DocumentContext | None, *, coerce_str_values: bool = False) -> Any`

```python
def my_deserializer(bson, expected_type_info, document_context=None, *, coerce_str_values=False):
    """Convert BSON back to pseudo-primitive objects."""
    expected_type = expected_type_info.type_
    
    if expected_type == datetime:
        return datetime.fromisoformat(bson)
    elif expected_type == Money:
        return Money(bson["amount"], bson["currency"])
    elif expected_type == list:
        return [deserialize_item(item) for item in bson]
    # ... handle other types
    
    return bson

type_registration.bson_to_pseudo_primitive.set_function(my_deserializer)
```

## Project Structure Example

```
myproject/
├── type_preparation.py          # Your type configuration
├── main.py                     # Import type_preparation here
├── models/
│   ├── user.py                 # BsonableDataclass types
│   ├── order.py
│   └── product.py
├── types/
│   ├── money.py                # Custom pseudo-primitive types
│   ├── email.py
│   └── custom_date.py
└── type_registration/          # This module (copied into your project)
    ├── __init__.py
    ├── README.md
    └── ...
```

## Advanced Usage

### Runtime Type Checking

```python
from type_registration import type_registry

# Check if a type is registered
if type_registry.is_primitive_cls(MyType):
    print("MyType is a primitive")

# Look up types by ID
user_class = type_registry.lookup_type_by_type_id("User")
if user_class:
    user = user_class(name="John", email="john@example.com")

# Get type ID from class
type_id = type_registry.type_to_type_id(User)
```

### Serialization

```python
from type_registration import type_registry

# Serialize any registered object
my_object = User(name="Alice", email="alice@example.com")
bson_data = type_registry.serialize(my_object)

# The registry handles all the type routing automatically
```

### Multiple Projects

The module is designed to be project-agnostic. Each project just needs its own `type_preparation.py` file with project-specific imports and configuration.

## Best Practices

1. **Single type_preparation file** per project
2. **Import early** - Import your type_preparation file at application startup
3. **Unique type IDs** - Ensure all your BsonableDataclass types have unique `__type_id__` values
4. **Comprehensive pseudo-primitives** - Include all custom types that need serialization
5. **Test your serialization** - Verify your custom serialization functions work correctly
6. **Document your types** - Add docstrings to your custom types explaining their purpose

## Migration from Hardcoded Registry

If you're migrating from a hardcoded type registry:

1. **Extract imports** from your old registry file into a `type_preparation.py` file
2. **Configure pseudo-primitives** by adding them to the `pseudo_primitives` list
3. **Move serialization logic** into the custom serialization functions
4. **Call `create_type_registry()`** after configuration
5. **Update imports** to use the new module-level registry

## Troubleshooting

### "Type not found" errors
- Ensure the type is imported in your `type_preparation.py` file
- Check that BsonableDataclass types have unique `__type_id__` values
- Verify `create_type_registry()` is called after all configuration

### Serialization errors
- Check that your custom serialization functions handle all registered pseudo-primitives
- Ensure deserialization function signature matches the expected format
- Test serialization/deserialization with sample data

### Database connection errors
- Verify `MONGO_URL` and `MONGO_DB_NAME` environment variables are set
- Check that your MongoDB server is running and accessible
- Ensure the database name specified in `MONGO_DB_NAME` exists or can be created

### Import errors
- Make sure `type_preparation.py` is imported before using the registry
- Check for circular imports between your types and the registry
- Verify all dependencies are properly installed

---

This module provides a flexible, reusable foundation for type registration and serialization in any Python project. The key is properly configuring your `type_preparation.py` file for your specific project's needs. 