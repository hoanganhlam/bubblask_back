from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.authentication.models import Profile
from django.contrib.auth.models import User


@receiver(post_save, sender=User)
def user_created(sender, instance, created, **kwargs):
    if created:
        setting = {
            "color": {
                "--task-color": "#FFF",
                "--task-text-color": "#333333",
                "--btn-color": "#cd2653",
                "--btn-text-color": "#FFF",
                "--bg-color-primary": "#fae0ca",
                "--bg-color-secondary": "#ffffff",
                "--bg-color-primary-text": "#333333",
                "--bg-color-secondary-text": "#333333",
                "background": None
            },
            "timer": {
                "tomato": 25,
                "short_break": 5,
                "long_break": 10,
                "is_strict": False
            },
            "task_order": [],
            "notification": {
                "wake_me": 5
            }
        }
        Profile.objects.create(user=instance, setting=setting)
