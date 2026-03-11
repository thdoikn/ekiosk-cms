from rest_framework import serializers
from .models import Region, Playlist, PlaylistItem, EKiosk, KioskLog
from media_manager.serializers import MediaSerializer


class RegionSerializer(serializers.ModelSerializer):
    active_playlist = serializers.SerializerMethodField()
    kiosk_count = serializers.SerializerMethodField()

    class Meta:
        model = Region
        fields = ['id', 'name', 'description', 'active_playlist', 'kiosk_count', 'created_at']

    def get_active_playlist(self, obj):
        if obj.active_playlist:
            return {'id': str(obj.active_playlist.id), 'name': obj.active_playlist.name}
        return None

    def get_kiosk_count(self, obj):
        return obj.kiosks.count()


class PlaylistItemSerializer(serializers.ModelSerializer):
    media = MediaSerializer(read_only=True)
    media_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = PlaylistItem
        fields = ['id', 'media', 'media_id', 'order', 'duration_seconds']


class PlaylistSerializer(serializers.ModelSerializer):
    items = PlaylistItemSerializer(many=True, read_only=True)
    assigned_regions = serializers.SerializerMethodField()

    class Meta:
        model = Playlist
        fields = ['id', 'name', 'assigned_regions', 'is_active', 'hash', 'items', 'created_at']
        read_only_fields = ['hash']

    def get_assigned_regions(self, obj):
        return [{'id': str(r.id), 'name': r.name} for r in obj.assigned_regions.all()]


class EKioskSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    region = RegionSerializer(read_only=True)
    region_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    active_playlist = serializers.SerializerMethodField()

    class Meta:
        model = EKiosk
        fields = [
            'id', 'name', 'region', 'region_id',
            'playlist_override', 'force_update', 'status',
            'last_heartbeat', 'last_ip_address', 'last_app_version',
            'last_os_version', 'last_storage_free', 'last_memory_free',
            'last_known_hash', 'is_active', 'registered_at', 'active_playlist',
            'latitude', 'longitude', 'stop_id',
        ]
        read_only_fields = ['status', 'last_heartbeat', 'registered_at']

    def get_active_playlist(self, obj):
        playlist = obj.get_active_playlist()
        if playlist:
            return {'id': playlist.id, 'name': playlist.name, 'hash': playlist.hash}
        return None


class HeartbeatSerializer(serializers.Serializer):
    playlist_hash = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    app_version = serializers.CharField(required=False, allow_blank=True)
    os_version = serializers.CharField(required=False, allow_blank=True)
    storage_free_bytes = serializers.IntegerField(required=False, allow_null=True)
    memory_free_bytes = serializers.IntegerField(required=False, allow_null=True)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)


class KioskCheckSerializer(serializers.Serializer):
    playlist_hash = serializers.CharField()
    force_update = serializers.BooleanField()
    status = serializers.CharField()


class ReorderSerializer(serializers.Serializer):
    items = serializers.ListField(
        child=serializers.DictField()
        # expects: [{"id": "uuid", "order": 1}, ...]
    )


class KioskLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = KioskLog
        fields = ['id', 'checked_at', 'reported_hash', 'ip_address', 'is_up_to_date']
