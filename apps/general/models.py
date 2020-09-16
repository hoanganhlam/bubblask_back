from django.db import models
from base.interface import Taxonomy, BaseModel
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField, JSONField
from django.contrib.auth.models import User
from utils.slug import unique_slugify


# Create your models here.


class HashTag(Taxonomy):
    for_models = ArrayField(models.CharField(max_length=50), null=True, blank=True)


class Message(BaseModel):
    user = models.ForeignKey(User, related_name="messages", on_delete=models.CASCADE)
    room = models.CharField(max_length=50)
    msg = models.CharField(max_length=150)
