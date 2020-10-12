from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.task.models import Board


@receiver(post_save, sender=Board)
def board_created(sender, instance, created, **kwargs):
    if instance.id and str(instance.id) not in instance.slug:
        instance.slug = instance.slug + "-" + str(instance.id)
        instance.save()
