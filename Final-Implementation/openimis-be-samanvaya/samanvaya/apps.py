from django.apps import AppConfig


class SamanvayaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "samanvaya"
    verbose_name = "Samanvaya Payment Engine"

    def ready(self):
        # Import signal handlers to register them
        import samanvaya.signal_handlers  # noqa: F401
