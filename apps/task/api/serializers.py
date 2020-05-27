from apps.task import models
from rest_framework import serializers


class BoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Board
        fields = '__all__'
        extra_kwargs = {
            'user': {'read_only': True}
        }

    def to_representation(self, instance):
        return super(BoardSerializer, self).to_representation(instance)


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Task
        fields = '__all__'
        extra_kwargs = {
            'user': {'read_only': True}
        }

    def to_representation(self, instance):
        return super(TaskSerializer, self).to_representation(instance)
