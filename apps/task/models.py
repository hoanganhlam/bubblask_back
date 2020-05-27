from django.db import models
from base.interface import BaseModel
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField, JSONField
from django.utils.translation import ugettext_lazy as _
from apps.general.models import HashTag
from apps.media.models import Media
from utils.slug import unique_slugify


# Create your models here.

def default_time():
    return {
        "time_start": 0,
        "time_done": 0,
        "stop_times": [],
        "remainder": 0
    }


class Board(BaseModel):
    title = models.CharField(max_length=200, null=True, blank=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    slug = models.CharField(max_length=200, blank=True)
    settings = JSONField(null=True, blank=True)
    is_interface = models.BooleanField(default=False)
    media = models.ForeignKey(Media, on_delete=models.SET_NULL, related_name="boards", null=True, blank=True)
    hash_tags = models.ManyToManyField(HashTag, related_name="boards", blank=True)
    user = models.ForeignKey(User, related_name="boards", on_delete=models.CASCADE)
    parent = models.ForeignKey('self', related_name="children", on_delete=models.SET_NULL, null=True, blank=True)
    members = models.ManyToManyField(User, blank=True, related_name="member_boards")

    def save(self, **kwargs):
        # generate unique slug
        if hasattr(self, 'slug') and self.slug is None or self.slug == '':
            unique_slugify(self, self.title)
        super(Board, self).save(**kwargs)


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
    times = ArrayField(JSONField(null=True, blank=True, default=default_time), null=True, blank=True)
    tomato = models.FloatField(default=25)
    is_bubble = models.BooleanField(default=False)
    settings = JSONField(null=True, blank=True)

    user = models.ForeignKey(User, related_name="tasks", on_delete=models.CASCADE)
    parent = models.ForeignKey('self', related_name="children", on_delete=models.SET_NULL, null=True, blank=True)
    board = models.ForeignKey(Board, related_name="tasks", on_delete=models.SET_NULL, null=True, blank=True)
