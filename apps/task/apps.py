from django.apps import AppConfig


class TaskConfig(AppConfig):
    name = 'apps.task'

    def ready(self):
        from apps.task import signals
