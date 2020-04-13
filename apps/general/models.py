from django.db import models
from base.interface import Taxonomy
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
# Create your models here.


class HashTag(Taxonomy):
    for_models = ArrayField(models.CharField(max_length=50), null=True, blank=True)
