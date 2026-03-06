from django.contrib import admin
from .models import Region, Playlist, PlaylistItem, EKiosk, KioskLog


class PlaylistItemInline(admin.TabularInline):
    model = PlaylistItem
    extra = 1


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['name', 'active_playlist', 'description', 'created_at']


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'hash', 'updated_at']
    inlines = [PlaylistItemInline]


@admin.register(EKiosk)
class EKioskAdmin(admin.ModelAdmin):
    list_display = ['name', 'region', 'status', 'last_heartbeat', 'is_active']
    readonly_fields = ['status', 'last_heartbeat', 'last_ip_address', 'registered_at']


@admin.register(KioskLog)
class KioskLogAdmin(admin.ModelAdmin):
    list_display = ['kiosk', 'checked_at', 'is_up_to_date', 'ip_address']
