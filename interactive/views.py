from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import InteractivePage
from .serializers import InteractivePageSerializer
from kiosk.models import EKiosk


class InteractivePageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InteractivePageSerializer

    def get_permissions(self):
        return [AllowAny()]

    def get_queryset(self):
        kiosk_id = self.request.query_params.get('kiosk_id')
        qs = InteractivePage.objects.filter(is_active=True)
        if kiosk_id:
            try:
                kiosk = EKiosk.objects.get(id=kiosk_id)
                if kiosk.region:
                    qs = qs.filter(regions=kiosk.region) | qs.filter(regions=None)
            except EKiosk.DoesNotExist:
                pass
        return qs.distinct().order_by('order')
