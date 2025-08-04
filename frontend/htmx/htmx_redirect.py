from .htmx_response import HtmxResponse, make_htmx_response


def htmx_redirect(full_path: str) -> HtmxResponse:
    response = make_htmx_response()
    response.add_redirect(full_path)
    return response