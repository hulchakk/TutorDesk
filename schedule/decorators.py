from functools import wraps
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect


def htmx_redirect_response(view_func):
    @wraps(view_func)
    def _wrapped_view(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        response = view_func(request, *args, **kwargs)

        if request.htmx and isinstance(response, HttpResponseRedirect):
            htmx_response = HttpResponse(status=200)
            htmx_response["HX-Redirect"] = response.url
            return htmx_response

        return response

    return _wrapped_view
