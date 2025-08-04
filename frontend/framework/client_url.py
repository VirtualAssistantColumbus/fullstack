from flask import g, request


def stash_client_url_into_g(client_url: str) -> None:
    """ Stashes the client's URL into Flask's g variable (a request-scoped variable). """
    g.client_url = client_url

def get_client_url() -> str:
    """ Returns the client's URL. 
    
    If in a post() request context, returns the URL stashed in Flask's g.
    Otherwise returns the URL from Flask's request object.
    """
    if hasattr(g, 'client_url'):
        return g.client_url
    return request.url

def get_client_path() -> str:
    """ Returns just the path portion of the client's URL (e.g. 'hello?id=5' from 'google.com/hello?id=5'). """
    from urllib.parse import urlparse
    url = get_client_url()
    parsed = urlparse(url)
    return parsed.path + ('?' + parsed.query if parsed.query else '')

def get_client_base_url() -> str:
    """ Returns just the base/root URL without path or query parameters (e.g. 'https://google.com' from 'https://google.com/hello?id=5'). """
    from urllib.parse import urlparse
    url = get_client_url()
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"