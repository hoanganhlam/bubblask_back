from django.db import models
from base.interface import BaseModel
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField, JSONField
from django.utils.translation import ugettext_lazy as _


# Create your models here.

def default_time():
    return {
        "time_start": 0,
        "time_done": 0,
        "stop_times": [],
        "remainder": 0
    }


class Task(BaseModel):
    CHOICE = (
        ("pending", _("pending")),
        ("running", _("running")),
        ("stopping", _("stopping")),
        ("stopped", _("stopped")),
        ("complete", _("complete")),
    )

    title = models.CharField(max_length=200, null=True, blank=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    interval = models.IntegerField(default=1)
    status = models.CharField(choices=CHOICE, default='OFF', max_length=20)
    user = models.ForeignKey(User, related_name="tasks", on_delete=models.CASCADE)
    times = ArrayField(JSONField(null=True, blank=True, default=default_time), null=True, blank=True)
    tomato = models.FloatField(default=25)
    is_bubble = models.BooleanField(default=False)
