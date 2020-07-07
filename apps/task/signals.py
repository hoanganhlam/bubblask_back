from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.task.models import Board
from apps.general.models import Workspace


@receiver(post_save, sender=Board)
def board_created(sender, instance, created, **kwargs):
    if created:
        if instance.ws is None:
            ws = Workspace(name=instance.title, user=instance.user)
            ws.save()
            instance.ws = ws
            instance.settings = {}
            instance.save()
    else:
        ws = instance.ws
        if ws:
            ws.name = instance.title
            is_public = instance.settings.get("is_public", False)
            if not is_public and instance.settings.get("password"):
                ws.password = instance.settings.get("password")
            ws.is_public = is_public
            ws.save()
