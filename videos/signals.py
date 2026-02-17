import shutil
from pathlib import Path
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
import django_rq
from django.conf import settings
from .models import Video
from .tasks import convert_video_to_hls


@receiver(post_save, sender=Video)
def video_post_save(sender, instance: Video, created: bool, **kwargs):
    """
    After video upload:
    enqueue HLS conversion in background.
    """

    if not instance.video_file:
        return

    def enqueue_task():
        queue = django_rq.get_queue("default")
        queue.enqueue(convert_video_to_hls, instance.pk)

    transaction.on_commit(enqueue_task)


@receiver(post_delete, sender=Video)
def video_post_delete(sender, instance: Video, **kwargs):
    """
    Cleanup files when video is deleted.
    """
    if instance.video_file:
        try:
            Path(instance.video_file.path).unlink(missing_ok=True)
        except Exception:
            pass

    if instance.thumbnail:
        try:
            Path(instance.thumbnail.path).unlink(missing_ok=True)
        except Exception:
            pass

    hls_dir = Path(settings.MEDIA_ROOT) / "hls" / str(instance.pk)
    if hls_dir.exists():
        shutil.rmtree(hls_dir)
