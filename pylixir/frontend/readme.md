# Pylixir Frontend Module

# IDE
- Use the VS Code extension: "Highlight f-strings" by jkmnt so that Html in f-strings is highlighted. You may need to register "Html" as a highlighting function.

## Setup
- Add "APP_PROTOCOL" to your environment variables. This should be one of: 'http' or 'https' (Defaults to https)
- Add "API_HOST" to your env variables. This is where htmxmethod routes will be registered. 
NOTE: The current implementation requires Flask host matching to work.

## Usage
# NOTE: In your app, you may need to set 
	expose_headers_list = [
		'Set-Cookie',
		"HX-Location",
		"HX-Push-Url",
		"HX-Redirect",
		"HX-Refresh",
		"HX-Replace-Url",
		"HX-Reswap",
		"HX-Retarget",
		"HX-Reselect",
		"HX-Trigger",
		"HX-Trigger-After-Settle",
		"HX-Trigger-After-Swap"
	]

### Registering Routes
To register all frontend routes with your Flask app:

1. First import all modules containing pages and routes
2. Then run the registration, which stores the routes into the module's state

```python
def create_app():
    # Import all your modules here
    
    # Then run the registration
    import pylixir.frontend
	pylixir.frontend.register_flask_routes(web_app)
```

The import step loads all the routes and pages into the module, and the registration step registers them with your Flask application.

### Adding Head Content and Scripts
After importing the frontend module, you can set global head content (CSS, external scripts, fonts) and custom JavaScript:

```python
import pylixir.frontend
from pylixir.frontend.utilities.html import Html

# Set head content (injected into <head> section)
pylixir.frontend.head = Html("""
    <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Caveat&display=swap" rel="stylesheet">
    <style>
        /* Custom styles */
    </style>
""")

# Set custom JavaScript (injected into <body> before closing tag)
pylixir.frontend.script = """
    // Custom initialization code
    console.log('App initialized');
"""
```

The framework automatically injects these into the HTML template when rendering pages. 