from __future__ import annotations
from pathlib import Path
from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from videos.models import Video
from videos.api.serializers import VideoSerializer


ALLOWED_RESOLUTIONS = {"480p", "720p", "1080p"}


def _get_hls_base_dir(movie_id: int, resolution: str) -> Path:
    """Return the base directory for HLS assets of a movie/resolution."""
    if resolution not in ALLOWED_RESOLUTIONS:
        raise Http404("Resolution not supported.")

    return Path(settings.MEDIA_ROOT) / "hls" / str(movie_id) / resolution


def _ensure_movie_exists(movie_id: int) -> None:
    """Raise 404 if the referenced movie does not exist."""
    if not Video.objects.filter(pk=movie_id).exists():
        raise Http404("Video not found.")


def _safe_segment_name(segment: str) -> str:
    """
    Prevent path traversal and only allow plain filenames.

    - Disallow slashes/backslashes
    - Disallow '..'
    - Keep only basename behavior
    """
    segment_path = Path(segment)
    if segment_path.name != segment:
        raise Http404("Invalid segment name.")
    if ".." in segment:
        raise Http404("Invalid segment name.")
    return segment


class VideoListView(generics.ListAPIView):
    """Return a list of all available videos (JWT required)."""

    serializer_class = VideoSerializer
    permission_classes = [IsAuthenticated]
    queryset = Video.objects.all()


class HlsIndexView(APIView):
    """Serve the HLS playlist (index.m3u8) for a movie and resolution (JWT required)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id: int, resolution: str):
        _ensure_movie_exists(movie_id)

        base_dir = _get_hls_base_dir(movie_id, resolution)
        manifest_path = base_dir / "index.m3u8"

        if not manifest_path.exists():
            raise Http404("Manifest not found.")

        # Content-Type required by the documentation.
        return FileResponse(
            open(manifest_path, "rb"),
            content_type="application/vnd.apple.mpegurl",
        )


class HlsSegmentView(APIView):
    """Serve a single HLS TS segment for a movie and resolution (JWT required)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, movie_id: int, resolution: str, segment: str):
        _ensure_movie_exists(movie_id)

        base_dir = _get_hls_base_dir(movie_id, resolution)
        safe_name = _safe_segment_name(segment)

        # Optional: restrict to .ts segments only
        if not safe_name.lower().endswith(".ts"):
            raise Http404("Segment not found.")

        segment_path = base_dir / safe_name
        if not segment_path.exists():
            raise Http404("Segment not found.")

        # Content-Type required by the documentation.
        return FileResponse(
            open(segment_path, "rb"),
            content_type="video/MP2T",
        )
