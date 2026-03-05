from rest_framework import serializers
from .models import InteractivePage


class InteractivePageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InteractivePage
        fields = ['id', 'slug', 'title', 'icon', 'url', 'order', 'is_active']
