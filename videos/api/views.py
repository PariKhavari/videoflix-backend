from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from videos.models import Video
from videos.api.serializers import VideoSerializer


class VideoListView(generics.ListAPIView):
    """Return a list of all available videos (JWT required)."""

    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticated]
    queryset = Video.objects.all()
