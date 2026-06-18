from django.urls import path
from . import views

urlpatterns = [
    path("webhook/gateway/", views.gateway_webhook, name="samanvaya-gateway-webhook"),
]
