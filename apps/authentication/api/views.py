from rest_framework import views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from apps.authentication.api.serializers import UserSerializer
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from rest_auth.registration.views import SocialLoginView
from rest_framework import viewsets, permissions
from base import pagination
from rest_framework.filters import OrderingFilter
from rest_framework_jwt.settings import api_settings
from rest_framework import status

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

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        if instance.id != request.user.id:
            return Response({})
        options = request.data.get("options")
        is_strict = request.data.get("is_strict")
        task_order = request.data.get("task_order")
        task_graph_setting = request.data.get("task_graph_setting")
        if instance.profile.setting is None:
            instance.profile.setting = {}
        if options:
            instance.profile.setting = options
            instance.profile.save()
        if is_strict is not None:
            if instance.profile.setting["timer"] is None:
                instance.profile.setting["timer"] = {}
            instance.profile.setting["timer"]["is_strict"] = is_strict
            instance.profile.save()
        if task_order is not None:
            instance.profile.setting["task_order"] = task_order
            instance.profile.save()
        if task_graph_setting is not None:
            instance.profile.setting["task_graph_setting"] = task_graph_setting
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
