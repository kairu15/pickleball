from django.urls import path
from . import webhooks

urlpatterns = [
    path('', webhooks.stripe_webhook, name='stripe_webhook'),
]
