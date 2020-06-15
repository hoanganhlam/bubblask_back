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


class WSSerializer(serializers.ModelSerializer):
    isPrivate = serializers.SerializerMethodField()
    board = serializers.SerializerMethodField()

    class Meta:
        model = models.Workspace
        fields = ['id', 'name', 'code', 'user', 'settings', 'isPrivate', 'board']
        extra_kwargs = {
            'code': {'read_only': True},
            'user': {'read_only': True}
        }

    def to_representation(self, instance):
        self.fields['user'] = UserSerializer(read_only=True)
        return super(WSSerializer, self).to_representation(instance)

    def get_board(self, instance):
        if hasattr(instance, 'board'):
            return BoardSerializer(instance.board).data
        else:
            return None

    def get_isPrivate(self, instance):
        if instance.password is not None:
            return True
        else:
            return False
