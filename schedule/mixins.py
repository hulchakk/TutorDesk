from django.http import HttpResponse


class HTMXFormMixin:
    def form_invalid(self, form) -> HttpResponse:
        response = super().form_invalid(form)

        if self.request.htmx:
            response.status_code = 422
            return response

        return response

    def form_valid(self, form) -> HttpResponse:
        response = super().form_valid(form)

        if self.request.htmx:
            success_url = self.get_success_url()
            response = HttpResponse(status=200)
            response["HX-Redirect"] = success_url
            return response

        return response
