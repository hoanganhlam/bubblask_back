from django.db import models
from base.interface import Taxonomy, BaseModel
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField, JSONField
from django.contrib.auth.models import User
from utils.slug import unique_slugify


# Create your models here.


class HashTag(Taxonomy):
    for_models = ArrayField(models.CharField(max_length=50), null=True, blank=True)


class Workspace(BaseModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=100)
    password = models.CharField(max_length=50, null=True, blank=True)
    members = models.ManyToManyField(User, blank=True, related_name="workspaces")
    user = models.ForeignKey(User, related_name="managed_workspaces", on_delete=models.CASCADE)
    settings = JSONField(blank=True, null=True)
    is_public = models.BooleanField(default=True)

    def save(self, **kwargs):
        unique_slugify(self, self.name, slug_field_name="code", slug_separator="_")
        super(Workspace, self).save(**kwargs)
