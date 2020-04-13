from apps.general import models
from rest_framework import serializers


class HashTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.HashTag
        fields = '__all__'
        extra_kwargs = {
            'slug': {'read_only': True}
        }

    def to_representation(self, instance):
        return super(HashTagSerializer, self).to_representation(instance)
