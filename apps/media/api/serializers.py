from apps.media import models
from rest_framework import serializers
from sorl.thumbnail import get_thumbnail
from apps.activity.actions import is_following
from django.contrib.auth.models import User
from apps.authentication.models import Profile

sizes = ['200_200', '600_200']


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['media', 'description', 'nick']

    def to_representation(self, instance):
        self.fields['media'] = MediaSerializer(read_only=True)
        return super(ProfileSerializer, self).to_representation(instance)


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'username', 'profile', 'is_following']

    def get_profile(self, instance):
        if hasattr(instance, 'profile'):
            return ProfileSerializer(instance.profile).data
        return None

    def get_is_following(self, instance):
        if self.context.get("request"):
            user = self.context.get("request").user
            if user.is_authenticated:
                return is_following(user, instance)
        return False


class MediaSerializer(serializers.ModelSerializer):
    sizes = serializers.SerializerMethodField()

    class Meta:
        model = models.Media
        fields = '__all__'
        extra_fields = ['sizes']

    def get_field_names(self, declared_fields, info):
        expanded_fields = super(MediaSerializer, self).get_field_names(declared_fields, info)

        if getattr(self.Meta, 'extra_fields', None):
            return expanded_fields + self.Meta.extra_fields
        else:
            return expanded_fields

    def get_sizes(self, instance):
        if instance.path:
            return {
                "thumb_270_270": get_thumbnail(instance.path, '270x270', crop='center', quality=100).url,
                "thumb_540_540": get_thumbnail(instance.path, '540x540', crop='center', quality=100).url,
                "resize": get_thumbnail(instance.path, '540', crop='noop', quality=100).url
            }
        else:
            return {}

    def to_representation(self, instance):
        # self.fields['user'] = UserSerializer(read_only=True)
        return super(MediaSerializer, self).to_representation(instance)
