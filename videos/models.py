from django.db import models

class Video(models.Model):
    """Stores video metadata required by the Videoflix API documentation."""

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100)

    # Uploads
    thumbnail = models.ImageField(upload_to="thumbnail/", blank=True, null=True) 
    video_file = models.FileField(upload_to="videos/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title
