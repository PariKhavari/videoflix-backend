# videos/signals.py
from __future__ import annotations
import shutil
from pathlib import Path
import django_rq
from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from videos.models import Video
from videos.tasks import convert_video_to_hls


def _hls_base_dir(video_id: int) -> Path:
    """MEDIA_ROOT/hls/<video_id>/"""
    return Path(settings.MEDIA_ROOT) / "hls" / str(video_id)


@receiver(post_save, sender=Video)
def video_post_save(sender, instance: Video, created: bool, **kwargs) -> None:
    """
    When a video is created/updated and has a video_file:
    enqueue background HLS conversion via Django RQ.
    """
    if not instance.video_file:
        return

    queue = django_rq.get_queue("default")
    queue.enqueue(convert_video_to_hls, instance.pk)


@receiver(post_delete, sender=Video)
def video_post_delete(sender, instance: Video, **kwargs) -> None:
    """
    Cleanup files on disk when model is deleted:
    - original uploaded video file
    - generated HLS folder for this video id
    - thumbnail (optional)
    """
    if instance.video_file:
        try:
            video_path = Path(instance.video_file.path)
            if video_path.exists():
                video_path.unlink()
        except Exception:
            pass

    if instance.thumbnail:
        try:
            thumb_path = Path(instance.thumbnail.path)
            if thumb_path.exists():
                thumb_path.unlink()
        except Exception:
            pass

    try:
        base_dir = _hls_base_dir(instance.pk)
        if base_dir.exists():
            shutil.rmtree(base_dir)
    except Exception:
        pass
