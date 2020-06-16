from rest_framework import views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from apps.authentication.api.serializers import UserSerializer, UserReportSerializer
from apps.media.models import Media
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from rest_auth.registration.views import SocialLoginView
from rest_framework import viewsets, permissions
from base import pagination
from rest_framework.filters import OrderingFilter
from rest_framework_jwt.settings import api_settings
from rest_framework import status
from rest_framework import serializers
from apps.task.models import Tracking, Task
from utils.pusher import pusher_client

jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER


class UserViewSet(viewsets.ModelViewSet):
    models = User
    queryset = models.objects.order_by('-id')
    serializer_class = UserSerializer
    permission_classes = permissions.AllowAny,
    pagination_class = pagination.Pagination
    filter_backends = [OrderingFilter]
    search_fields = ['first_name', 'last_name', 'username']
    lookup_field = 'username'
    lookup_value_regex = '[\w.@+-]+'

    def list(self, request, *args, **kwargs):
        self.serializer_class = UserReportSerializer
        return super(UserViewSet, self).list(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        if instance.id != request.user.id:
            return Response({})
        ws = instance.profile.setting.get("ws", 0)
        user_status = request.data.get("status")
        profile = request.data.get("profile")
        options = request.data.get("options")
        is_strict = request.data.get("is_strict")
        task_order = request.data.get("task_order")
        task_graph_setting = request.data.get("task_graph_setting")
        time_zone = request.data.get("time_zone")
        if instance.profile.setting is None:
            instance.profile.setting = {}
        if instance.profile.extra is None:
            instance.profile.extra = {}
        if options:
            for key in options.keys():
                instance.profile.setting[key] = options[key]
        if is_strict is not None:
            if instance.profile.setting["timer"] is None:
                instance.profile.setting["timer"] = {}
            instance.profile.setting["timer"]["is_strict"] = is_strict
        if task_order is not None:
            instance.profile.setting["task_order"] = task_order
            instance.profile.save()
        if task_graph_setting is not None:
            instance.profile.setting["task_graph_setting"] = task_graph_setting
        if profile:
            instance.profile.links = profile.get("links")
            instance.profile.bio = profile.get("bio")
            instance.profile.extra = profile.get("extra")
            media = profile.get("media")
            if media:
                media_instance = Media.objects.get(pk=int(media))
                instance.profile.media = media_instance
        if time_zone:
            instance.profile.time_zone = time_zone
        if user_status:
            instance.profile.extra["status"] = user_status
            if ws is not None and ws != 0:
                pusher_client.trigger('ws_' + str(ws), 'change-user-status', {
                    "user": instance.id,
                    "status": user_status
                })
        instance.profile.save()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserExt(views.APIView):
    @api_view(['GET'])
    @permission_classes((IsAuthenticated,))
    def get_request_user(request, format=None):
        return Response(UserSerializer(request.user).data)
        # with connection.cursor() as cursor:
        #     cursor.execute("SELECT FETCH_USER_ID(%s)", [request.user.id])
        #     out = cursor.fetchone()[0]
        # return Response(out)


class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter


class FacebookConnect(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter


class GoogleConnect(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter


class TrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tracking
        fields = '__all__'


@api_view(['GET'])
def report(request, pk):
    user = User.objects.get(pk=pk)
    tracking = user.tracking.filter(user=user)
    tasks = Task.objects.filter(user=user)
    complete_tasks = tasks.filter(status="complete")
    accurate_estimates_arr = list(
        map(lambda x: abs(60 * x.tomato * x.interval - x.take_time) / 60 * x.tomato * x.interval,
            list(complete_tasks)))
    mean_accurate_estimates = sum(accurate_estimates_arr) / len(accurate_estimates_arr)
    return Response({
        "total_task_done": complete_tasks.count(),
        "total_task_delay": tasks.filter(status="stopped").count(),
        "accurate_estimates": mean_accurate_estimates,  # in second
        "tracking": TrackingSerializer(tracking, many=True).data,
    })
