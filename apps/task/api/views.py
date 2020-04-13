from rest_framework import viewsets, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
from base import pagination
from . import serializers
from apps.task import models
from rest_framework.response import Response


class TaskViewSet(viewsets.ModelViewSet):
    models = models.Task
    queryset = models.objects.order_by('-id')
    serializer_class = serializers.TaskSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['title', 'description']
    lookup_field = 'pk'

    def list(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            queryset = models.Task.objects.filter(
                user=request.user,
                status__in=["pending", "stopping", "running"],
                is_bubble=False
            ).order_by('-id')
            return Response(serializers.TaskSerializer(queryset, many=True).data)
        return Response([])

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
