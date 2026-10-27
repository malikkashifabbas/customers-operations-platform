from django.apps import AppConfig


class EventbusConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'infra.eventbus'
    label = 'eventbus'
