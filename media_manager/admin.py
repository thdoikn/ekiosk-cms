from django.contrib import admin
from .models import Media


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ['name', 'media_type', 'file_size', 'uploaded_by', 'created_at']
    readonly_fields = ['checksum', 'file_size']
