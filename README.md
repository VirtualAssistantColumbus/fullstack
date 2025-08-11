# Pylixir Framework

A type-safe fullstack Python web framework with document handling and HTMX integration.

## Features

🎯 **Type-Safe Document Management**
- MongoDB integration with type-safe ODM
- Document versioning and field validation  
- Configurable schema validation

🌐 **Modern Frontend Framework**
- HTMX integration for reactive UIs
- Server-side rendering support
- Built-in component system

🔐 **Authentication & Security**
- Flask-Login integration
- Role-based access control
- Secure session management

⚡ **Developer Experience**
- Auto-generating forms from document schemas
- Built-in development utilities
- Hot reload support

## Installation

### From Private Git Repository

```bash
pip install git+https://github.com/yourusername/pylixir.git
```

### From Local Source

```bash
cd /path/to/pylixir
pip install -e .
```

## Quick Start

```python
from pylixir.frontend import register_flask_routes
from pylixir.document import Document
from pylixir.typing import type_registry

# Initialize your Flask app
app = Flask(__name__)

# Register pylixir routes
register_flask_routes(app)

# Define your documents
class User(Document):
    name: str
    email: str
    
# Create type registry
create_type_registry()

# Run your app
if __name__ == "__main__":
    app.run(debug=True)
```

## Environment Setup

Set these environment variables:

```bash
APP_PROTOCOL=http  # or https
API_HOST=localhost:5000
```

## Documentation

See the individual module READMEs:
- [Frontend](frontend/readme.md) - HTMX and component system
- [Document](document/readme.txt) - Document management and MongoDB
- [Typing](typing/README.md) - Type system and validation

## Development

This library is actively developed and maintained privately.

## License

Proprietary - All rights reserved.