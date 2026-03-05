from rest_framework import serializers
from .models import Region, Playlist, PlaylistItem, EKiosk, KioskLog
from media_manager.serializers import MediaSerializer


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'name', 'description', 'created_at']


class PlaylistItemSerializer(serializers.ModelSerializer):
    media = MediaSerializer(read_only=True)
    media_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = PlaylistItem
        fields = ['id', 'media', 'media_id', 'order', 'duration_seconds']


class PlaylistSerializer(serializers.ModelSerializer):
    items = PlaylistItemSerializer(many=True, read_only=True)
    region = RegionSerializer(read_only=True)
    region_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Playlist
        fields = ['id', 'name', 'region', 'region_id', 'is_active', 'hash', 'items', 'created_at']
        read_only_fields = ['hash']


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
            'last_known_hash', 'is_active', 'registered_at', 'active_playlist'
        ]
        read_only_fields = ['status', 'last_heartbeat', 'registered_at']

    def get_active_playlist(self, obj):
        playlist = obj.get_active_playlist()
        if playlist:
            return {'id': playlist.id, 'name': playlist.name, 'hash': playlist.hash}
        return None


class HeartbeatSerializer(serializers.Serializer):
    current_hash = serializers.CharField(max_length=64)
    app_version = serializers.CharField(max_length=50, required=False, default='')
    os_version = serializers.CharField(max_length=50, required=False, default='')
    storage_free_bytes = serializers.IntegerField(required=False, default=0)
    memory_free_bytes = serializers.IntegerField(required=False, default=0)


class KioskCheckSerializer(serializers.Serializer):
    playlist_hash = serializers.CharField()
    force_update = serializers.BooleanField()
    status = serializers.CharField()


class ReorderSerializer(serializers.Serializer):
    items = serializers.ListField(
        child=serializers.DictField()
        # expects: [{"id": "uuid", "order": 1}, ...]
    )
