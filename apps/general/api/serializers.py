from apps.general import models
from rest_framework import serializers
from apps.authentication.api.serializers import UserSerializer


class HashTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.HashTag
        fields = '__all__'
        extra_kwargs = {
            'slug': {'read_only': True}
        }

    def to_representation(self, instance):
        return super(HashTagSerializer, self).to_representation(instance)


class WSSerializer(serializers.ModelSerializer):
    isPrivate = serializers.SerializerMethodField()

    class Meta:
        model = models.Workspace
        fields = ['id', 'name', 'code', 'members', 'user', 'setting', 'isPrivate']
        extra_kwargs = {
            'code': {'read_only': True},
            'user': {'read_only': True}
        }

    def to_representation(self, instance):
        self.fields['user'] = UserSerializer(read_only=True)
        return super(WSSerializer, self).to_representation(instance)

    def get_isPrivate(self, instance):
        if instance.password is not None:
            return True
        else:
            return False
