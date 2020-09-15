from django.db import models
from base.interface import BaseModel
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField, JSONField
from django.utils.translation import ugettext_lazy as _
from apps.general.models import HashTag
from apps.media.models import Media
from utils.slug import unique_slugify
from django.utils import timezone


# Create your models here.

def default_time():
    return {
        "time_start": 0,
        "time_done": 0,
        "stop_times": [],
        "remainder": 0
    }


# Use public board and private board
class Board(BaseModel):
    title = models.CharField(max_length=200, null=True, blank=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    slug = models.CharField(max_length=200, blank=True)
    kind = models.CharField(max_length=50, default="DEFAULT")  # GHOST, DEFAULT, TEMPLATE

    is_private = models.BooleanField(default=False)
    password = models.CharField(max_length=500, null=True, blank=True)

    settings = JSONField(null=True, blank=True)
    media = models.ForeignKey(Media, on_delete=models.SET_NULL, related_name="boards", null=True, blank=True)
    hash_tags = models.ManyToManyField(HashTag, related_name="boards", blank=True)
    user = models.ForeignKey(User, related_name="boards", on_delete=models.CASCADE)
    parent = models.ForeignKey('self', related_name="children", on_delete=models.SET_NULL, null=True, blank=True)
    members = models.ManyToManyField(User, through="BoardMember", related_name="member_boards", blank=True)

    def save(self, **kwargs):
        # generate unique slug
        if hasattr(self, 'slug') and self.slug is None or self.slug == '':
            unique_slugify(self, self.title)
        super(Board, self).save(**kwargs)


class BoardMember(BaseModel):
    user = models.ForeignKey(User, related_name="board_members", on_delete=models.CASCADE)
    board = models.ForeignKey(Board, related_name="board_members", on_delete=models.CASCADE)


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
    status = models.CharField(choices=CHOICE, default='pending', max_length=20)
    times = ArrayField(JSONField(null=True, blank=True, default=default_time), null=True, blank=True)
    tomato = models.FloatField(default=25)
    is_bubble = models.BooleanField(default=False)
    settings = JSONField(null=True, blank=True)

    user = models.ForeignKey(User, related_name="tasks", on_delete=models.CASCADE)
    assignee = models.ForeignKey(User, related_name="assigned_tasks", on_delete=models.CASCADE, null=True, blank=True)
    reporter = models.ForeignKey(User, related_name="reported_tasks", on_delete=models.CASCADE, null=True, blank=True)

    parent = models.ForeignKey('self', related_name="children", on_delete=models.SET_NULL, null=True, blank=True)
    board = models.ForeignKey(Board, related_name="tasks", on_delete=models.SET_NULL, null=True, blank=True)

    take_time = models.FloatField(default=0)


class Tracking(models.Model):
    # Time to deep work
    # How many time to work on a day
    # Total time spend to work all time
    # Total task work done
    # Total task skipped
    user = models.ForeignKey(User, related_name="tracking", on_delete=models.CASCADE)
    board = models.ForeignKey(Board, related_name="tracking", on_delete=models.CASCADE, null=True, blank=True)
    # time_start
    # time_stop
    # time_taken
    # task
    # ws
    data = ArrayField(JSONField(null=True, blank=True), null=True, blank=True)
    date_record = models.DateField(default=timezone.now)
    time_zone = models.IntegerField(default=0)
