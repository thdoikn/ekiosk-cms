from django.contrib.auth.models import User
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_active', 'is_staff', 'is_superuser',
            'date_joined', 'last_login',
        ]
        read_only_fields = ['date_joined', 'last_login', 'is_superuser']


class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'is_staff']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password     = serializers.CharField(min_length=8)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('date_joined')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateUserSerializer
        return UserSerializer

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        if user.is_superuser:
            return Response({'detail': 'Cannot deactivate superuser.'}, status=400)
        user.is_active = False
        user.save()
        return Response({'status': 'deactivated'})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({'status': 'activated'})

    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data['current_password']):
            return Response({'detail': 'Password lama salah.'}, status=400)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'status': 'password changed'})
