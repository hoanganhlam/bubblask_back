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


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Message
        fields = ['id', 'user', 'room', 'msg', 'created']
        extra_kwargs = {
            'user': {'read_only': True}
        }

    def to_representation(self, instance):
        self.fields['user'] = UserSerializer(read_only=True)
        return super(MessageSerializer, self).to_representation(instance)
