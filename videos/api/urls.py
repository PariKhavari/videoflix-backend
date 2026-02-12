from django.urls import path
from videos.api.views import VideoListView, HlsIndexView, HlsSegmentView

urlpatterns = [
    path("video/", VideoListView.as_view(), name="video-list"),
    path("video/<int:movie_id>/<str:resolution>/index.m3u8", HlsIndexView.as_view(), name="hls-index"),
    path("video/<int:movie_id>/<str:resolution>/<str:segment>/", HlsSegmentView.as_view(), name="hls-segment"),
]
