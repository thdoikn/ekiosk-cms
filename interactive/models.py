import uuid
from django.db import models
from kiosk.models import Region


class InteractivePage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    icon = models.CharField(max_length=50, blank=True)
    url = models.URLField()
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)
    regions = models.ManyToManyField(Region, blank=True, related_name='interactive_pages')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title
