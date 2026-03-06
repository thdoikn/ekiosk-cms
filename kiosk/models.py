import uuid
import hashlib
import json
from django.db import models
from django.utils import timezone


class Region(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    active_playlist = models.ForeignKey('Playlist', on_delete=models.SET_NULL,
                                        null=True, blank=True,
                                        related_name='assigned_regions')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Playlist(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def compute_hash(self):
        items = self.items.order_by('order').values(
            'media_id', 'order', 'duration_seconds'
        )
        raw = json.dumps(list(items), sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def save(self, *args, **kwargs):
        # only compute hash if already has pk (items exist)
        if self.pk:
            self.hash = self.compute_hash()
        super().save(*args, **kwargs)


class PlaylistItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='items')
    media = models.ForeignKey('media_manager.Media', on_delete=models.PROTECT, related_name='playlist_items')
    order = models.PositiveSmallIntegerField()
    duration_seconds = models.PositiveIntegerField()

    class Meta:
        ordering = ['order']
        unique_together = [['playlist', 'order']]

    def __str__(self):
        return f"{self.playlist.name} - #{self.order}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # recompute playlist hash when item changes
        self.playlist.save()


class EKiosk(models.Model):

    class Status(models.TextChoices):
        ONLINE = 'online', 'Online'
        OFFLINE = 'offline', 'Offline'
        STALE = 'stale', 'Stale Content'
        NEVER = 'never_connected', 'Never Connected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True, related_name='kiosks')
    playlist_override = models.ForeignKey(Playlist, on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='kiosk_overrides')
    force_update = models.BooleanField(default=False)

    # Heartbeat diagnostics
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    heartbeat_interval = models.PositiveIntegerField(default=300)  # seconds
    last_ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_app_version = models.CharField(max_length=50, blank=True)
    last_os_version = models.CharField(max_length=50, blank=True)
    last_storage_free = models.PositiveBigIntegerField(null=True, blank=True)
    last_memory_free = models.PositiveBigIntegerField(null=True, blank=True)
    last_known_hash = models.CharField(max_length=64, blank=True)

    is_active = models.BooleanField(default=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_active_playlist(self):
        if self.playlist_override and self.playlist_override.is_active:
            return self.playlist_override
        if self.region and self.region.active_playlist:
            return self.region.active_playlist
        return None

    @property
    def status(self):
        if not self.last_heartbeat:
            return self.Status.NEVER
        delta = timezone.now() - self.last_heartbeat
        threshold = self.heartbeat_interval * 3
        if delta.total_seconds() > threshold:
            return self.Status.OFFLINE
        playlist = self.get_active_playlist()
        if playlist and self.last_known_hash != playlist.hash:
            return self.Status.STALE
        return self.Status.ONLINE


class KioskLog(models.Model):
    kiosk = models.ForeignKey(EKiosk, on_delete=models.CASCADE, related_name='logs')
    checked_at = models.DateTimeField(auto_now_add=True)
    reported_hash = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_up_to_date = models.BooleanField()

    class Meta:
        ordering = ['-checked_at']
