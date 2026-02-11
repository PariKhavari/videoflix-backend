from rest_framework import serializers
from videos.models import Video

class VideoSerializer(serializers.ModelSerializer):
    """Serializer matching the exact /api/video/ response schema."""

    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = ("id", "created_at", "title", "description", "thumbnail_url", "category")

    def get_thumbnail_url(self, obj: Video) -> str | None:
        """Return an absolute URL for the thumbnail if available."""
        if not obj.thumbnail:
            return None

        request = self.context.get("request")
        url = obj.thumbnail.url
        return request.build_absolute_uri(url) if request else url
