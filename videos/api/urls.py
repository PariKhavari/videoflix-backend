from django.urls import path
from videos.api.views import VideoListView

urlpatterns = [
    path("video/", VideoListView.as_view(), name="video-list"),
]
