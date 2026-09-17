from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse


class HTMXFormMixin:
    def form_invalid(self, form) -> HttpResponse:
        response = super().form_invalid(form)

        if self.request.htmx:
            response.status_code = 200
            return response

        return response

    def form_valid(self, form) -> HttpResponse:
        try:
            response = super().form_valid(form)
        except (ValidationError, IntegrityError) as e:
            if isinstance(e, IntegrityError):
                form.add_error(None, "An entry with these details already exists.")
            elif hasattr(e, "message_dict"):
                for field, errors in e.message_dict.items():
                    for error in errors:
                        form.add_error(field if field != "__all__" else None, error)
            else:
                form.add_error(None, e)

            return self.form_invalid(form)

        if self.request.htmx:
            success_url = self.get_success_url()
            response = HttpResponse(status=200)
            response["HX-Redirect"] = success_url
            return response

        return response
