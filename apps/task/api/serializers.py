from apps.task import models
from apps.general.api.serializers import HashTagSerializer
from apps.media.api.serializers import MediaSerializer
from rest_framework import serializers


class BoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Board
        fields = '__all__'
        extra_kwargs = {
            'user': {'read_only': True}
        }

    def to_representation(self, instance):
        self.fields['hash_tags'] = HashTagSerializer(read_only=True, many=True)
        self.fields['media'] = MediaSerializer(read_only=True)
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
