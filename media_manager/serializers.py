from rest_framework import serializers
from .models import Media


class MediaSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Media
        fields = [
            'id', 'name', 'file', 'file_url', 'media_type',
            'checksum', 'file_size', 'duration_seconds',
            'uploaded_by', 'created_at'
        ]
        read_only_fields = ['checksum', 'file_size', 'file_url', 'uploaded_by', 'created_at']
