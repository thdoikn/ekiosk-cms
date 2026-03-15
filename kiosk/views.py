from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Max
from django.db import transaction

from .models import Region, Playlist, PlaylistItem, EKiosk, KioskLog
from .serializers import (
    RegionSerializer, PlaylistSerializer, PlaylistItemSerializer,
    EKioskSerializer, HeartbeatSerializer, ReorderSerializer, KioskLogSerializer
)
from media_manager.models import Media


class RegionViewSet(viewsets.ModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer

    @action(detail=True, methods=['post'], url_path='assign-playlist')
    def assign_playlist(self, request, pk=None):
        region = self.get_object()
        playlist_id = request.data.get('playlist_id')
        if not playlist_id:
            region.active_playlist = None
            region.save()
            return Response({'status': 'playlist unassigned'})
        playlist = get_object_or_404(Playlist, id=playlist_id)
        region.active_playlist = playlist
        region.save()
        return Response({'status': 'playlist assigned', 'playlist': playlist.name})


class PlaylistViewSet(viewsets.ModelViewSet):
    queryset = Playlist.objects.prefetch_related('items__media').all()
    serializer_class = PlaylistSerializer

    @action(detail=True, methods=['post'], url_path='reorder-items')
    def reorder(self, request, pk=None):
        playlist = self.get_object()
        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Step 1: shift all orders to a high range to avoid unique conflicts
        # e.g. order 1,2,3 → 1001,1002,1003 temporarily
        for item_data in serializer.validated_data['items']:
            PlaylistItem.objects.filter(
                id=item_data['id'], playlist=playlist
            ).update(order=item_data['order'] + 1000)

        # Step 2: now set the real target orders (no conflicts possible)
        for item_data in serializer.validated_data['items']:
            PlaylistItem.objects.filter(
                id=item_data['id'], playlist=playlist
            ).update(order=item_data['order'])

        playlist.save()  # recompute hash
        return Response({'status': 'reordered', 'hash': playlist.hash})

    @action(detail=True, methods=['post'], url_path='items')
    def add_item(self, request, pk=None):
        playlist = self.get_object()
        media_id = request.data.get('media_id')
        duration_seconds = request.data.get('duration_seconds', 10)

        media = get_object_or_404(Media, id=media_id)

        # auto-assign next order to avoid unique_together conflict
        last_order = playlist.items.aggregate(
            max_order=Max('order')
        )['max_order'] or 0

        item = PlaylistItem.objects.create(
            playlist=playlist,
            media=media,
            order=last_order + 1,
            duration_seconds=duration_seconds,
        )
        # playlist.save() is called by PlaylistItem.save() signal already
        return Response(PlaylistItemSerializer(item).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch', 'delete'], url_path='items/(?P<item_id>[^/.]+)')
    def item_detail(self, request, pk=None, item_id=None):
        playlist = self.get_object()
        item = get_object_or_404(PlaylistItem, id=item_id, playlist=playlist)

        if request.method == 'DELETE':
            item.delete()
            playlist.save()  # recompute hash
            return Response(status=status.HTTP_204_NO_CONTENT)

        # PATCH
        duration = request.data.get('duration_seconds')
        if duration is not None:
            item.duration_seconds = int(duration)
            item.save()  # triggers playlist hash recompute via PlaylistItem.save()
        return Response(PlaylistItemSerializer(item).data)


class EKioskViewSet(viewsets.ModelViewSet):
    queryset = EKiosk.objects.select_related('region', 'playlist_override').all()
    serializer_class = EKioskSerializer

    def get_permissions(self):
        # register and heartbeat are called by Flutter, no JWT needed
        if self.action in ['register', 'heartbeat', 'check', 'playlist', 'confirm_update', 'interactive_pages']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_authenticators(self):
        # Flutter endpoints send no cookies — skip SessionAuthentication to avoid CSRF enforcement
        # self.action is not yet set when get_authenticators() is called, so guard with hasattr
        if hasattr(self, 'action') and self.action in ['register', 'heartbeat', 'check', 'playlist', 'confirm_update', 'interactive_pages']:
            return []
        return super().get_authenticators()

    @action(detail=False, methods=['post'])
    def register(self, request):
        kiosk_id = request.data.get('kiosk_id')
        if not kiosk_id:
            return Response({'detail': 'kiosk_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        name = request.data.get('name', 'Unknown Kiosk')
        region_id = request.data.get('region_id')

        kiosk, created = EKiosk.objects.get_or_create(
            id=kiosk_id,
            defaults={
                'name': name,
                'region_id': region_id,
            }
        )

        return Response(
            EKioskSerializer(kiosk).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        kiosk = self.get_object()
        qs = kiosk.logs.all()
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(KioskLogSerializer(page, many=True).data)

    @action(detail=True, methods=['get'])
    def playlist(self, request, pk=None):
        kiosk = self.get_object()
        playlist = kiosk.get_active_playlist()
        if not playlist:
            return Response({'detail': 'No active playlist assigned.'}, status=404)
        return Response(PlaylistSerializer(playlist).data)

    @action(detail=True, methods=['post'])
    def heartbeat(self, request, pk=None):
        # Use get_object_or_404 to return 404 (not 500) when kiosk doesn't exist,
        # while keeping the deeper select_related for the playlist hash lookup.
        kiosk = get_object_or_404(
            self.get_queryset().select_related(
                'playlist_override',
                'region__active_playlist',
            ),
            pk=pk,
        )

        serializer = HeartbeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ip = (
            request.META.get('HTTP_X_REAL_IP')
            or request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            or request.META.get('REMOTE_ADDR')
        )

        now = timezone.now()
        playlist_hash = data.get('playlist_hash') or ''
        app_version = data.get('app_version', '')
        os_version = data.get('os_version', '')
        storage_free = data.get('storage_free_bytes')
        memory_free = data.get('memory_free_bytes')
        app_state = data.get("app_state", "")

        was_offline = kiosk.status in (kiosk.Status.OFFLINE, kiosk.Status.NEVER)

        playlist = kiosk.get_active_playlist()
        expected_hash = playlist.hash if playlist else None
        is_up_to_date = not expected_hash or playlist_hash == expected_hash

        kiosk.last_heartbeat = now
        kiosk.last_known_hash = playlist_hash
        kiosk.last_ip_address = ip
        kiosk.last_app_version = app_version
        kiosk.last_os_version = os_version
        kiosk.last_storage_free = storage_free
        kiosk.last_memory_free = memory_free

        update_fields = [
            'last_heartbeat', 'last_known_hash', 'last_ip_address',
            'last_app_version', 'last_os_version',
            'last_storage_free', 'last_memory_free',
        ]

        # Only update coordinates when the device actually sends them —
        # avoids wiping previously stored GPS on heartbeats without location data.
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        if latitude is not None:
            kiosk.latitude = latitude
            update_fields.append('latitude')
        if longitude is not None:
            kiosk.longitude = longitude
            update_fields.append('longitude')

        if was_offline and kiosk.offline_notified_at:
            kiosk.offline_notified_at = None
            update_fields.append('offline_notified_at')

        if app_state:
            kiosk.last_app_state = app_state
            update_fields.append("last_app_state")

        with transaction.atomic():
            kiosk.save(update_fields=update_fields)

            kiosk.logs.create(
                reported_hash=playlist_hash,
                ip_address=ip,
                is_up_to_date=is_up_to_date,
                app_version=app_version,
                storage_free=storage_free,
                memory_free=memory_free,
                app_state=app_state,
            )

        return Response({
            'status': kiosk.status,
            'force_update': kiosk.force_update,
            'playlist_hash': expected_hash,
        })

    @action(detail=True, methods=['post'], url_path='confirm-update')
    def confirm_update(self, request, pk=None):
        kiosk = self.get_object()
        kiosk.force_update = False
        kiosk.save()
        return Response({'status': 'confirmed'})

    @action(detail=True, methods=['post'], url_path='force-update')
    def force_update(self, request, pk=None):
        kiosk = self.get_object()
        kiosk.force_update = True
        kiosk.save()
        return Response({'status': 'force update triggered'})

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        kiosks = EKiosk.objects.all()
        total = kiosks.count()
        statuses = [k.status for k in kiosks]
        return Response({
            'total': total,
            'online': statuses.count('online'),
            'offline': statuses.count('offline'),
            'stale': statuses.count('stale'),
            'never_connected': statuses.count('never_connected'),
        })
