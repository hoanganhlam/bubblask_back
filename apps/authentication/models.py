from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField, ArrayField
from sorl.thumbnail import ImageField
import os
import datetime
from uuid import uuid4
from django.core.exceptions import ValidationError
from django.core.files.temp import NamedTemporaryFile
from urllib.parse import urlparse
import requests
from django.core.files import File


def validate_file_size(value):
    file_size = value.size

    if file_size > 10485760:
        raise ValidationError("The maximum file size that can be uploaded is 10MB")
    else:
        return value


def re_path(instance, filename, bucket):
    now = datetime.datetime.now()
    upload_to = '{}/guess/{}/'.format(bucket, str(now.year) + str(now.month) + str(now.day))
    ext = filename.split('.')[-1]
    filename = '{}.{}'.format(uuid4().hex, ext)
    return os.path.join(upload_to, filename)


def path_and_rename(instance, filename):
    return re_path(instance, filename, 'bubblask/images')


class Profile(models.Model):
    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    nick = models.CharField(max_length=200, null=True, blank=True)
    bio = models.CharField(max_length=500, null=True, blank=True)
    medals = ArrayField(models.CharField(max_length=80), null=True, blank=True)
    media = ImageField(upload_to=path_and_rename, max_length=500, validators=[validate_file_size])
    extra = JSONField(blank=True, null=True)
    setting = JSONField(blank=True, null=True)

    def save_url(self, url, **extra_fields):
        if url is None:
            return None
        name = urlparse(url).path.split('/')[-1]
        temp = NamedTemporaryFile(delete=True)
        try:
            req = requests.get(url=url, headers={'User-Agent': 'Mozilla/5.0'}, allow_redirects=True)
            disposition = req.headers.get("Content-Disposition")
            if disposition:
                test = disposition.split("=")
                if len(test) > 1:
                    name = test[1].replace("\"", "")
            temp.write(req.content)
            ext = name.split('.')[-1]
            if ext == '':
                ext = 'jpg'
                name = name + '.' + ext
            if ext in ['jpg', 'jpeg', 'png']:
                temp.flush()
                self.media.save(name, File(temp))
            return None
        except Exception as e:
            print(e)
            return None
