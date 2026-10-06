from django.contrib import admin

from subscriptions.models import TariffPlan, StudentSubscription

admin.site.register(TariffPlan)
admin.site.register(StudentSubscription)
