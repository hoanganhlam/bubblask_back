from apps.general import models
from rest_framework import serializers
from apps.authentication.api.serializers import UserSerializer
from apps.task.models import Board


class HashTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.HashTag
        fields = '__all__'
        extra_kwargs = {
            'slug': {'read_only': True}
        }

    def to_representation(self, instance):
        return super(HashTagSerializer, self).to_representation(instance)


class BoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Board
        fields = ['id', 'title', 'slug', 'settings']
        extra_kwargs = {}

    def to_representation(self, instance):
        return super(BoardSerializer, self).to_representation(instance)
