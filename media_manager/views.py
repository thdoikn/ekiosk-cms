from rest_framework import viewsets
from .models import Media
from .serializers import MediaSerializer


class MediaViewSet(viewsets.ModelViewSet):
    queryset = Media.objects.all().order_by('-created_at')
    serializer_class = MediaSerializer

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
