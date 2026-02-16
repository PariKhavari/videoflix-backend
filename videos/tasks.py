# videos/tasks.py
from __future__ import annotations
import os
import subprocess
from pathlib import Path
from django.conf import settings
from django.db import transaction
from videos.models import Video


ALLOWED_RESOLUTIONS = {
    "480p": {"height": 480, "video_bitrate": "1000k", "audio_bitrate": "128k"},
    "720p": {"height": 720, "video_bitrate": "2500k", "audio_bitrate": "128k"},
    "1080p": {"height": 1080, "video_bitrate": "5000k", "audio_bitrate": "192k"},
}


def _hls_output_dir(video_id: int, resolution: str) -> Path:
    """media/hls/<video_id>/<resolution>/"""
    return Path(settings.MEDIA_ROOT) / "hls" / str(video_id) / resolution


def _run(cmd: list[str]) -> None:
    """Run a command and raise a helpful error if it fails."""
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "FFmpeg failed.\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}\n"
        )


def convert_video_to_hls(video_id: int) -> None:
    """
    RQ Task:
    - loads Video
    - converts video_file to HLS playlists + segments for 480p/720p/1080p
    - writes files into media/hls/<id>/<resolution>/
    """
    video = Video.objects.filter(pk=video_id).first()
    if not video:
        raise RuntimeError(f"Video {video_id} not found.")

    if not video.video_file:
        raise RuntimeError(f"Video {video_id} has no video_file uploaded.")

    input_path = Path(video.video_file.path)
    if not input_path.exists():
        raise RuntimeError(f"Input file does not exist: {input_path}")


    for res, cfg in ALLOWED_RESOLUTIONS.items():
        out_dir = _hls_output_dir(video.id, res)
        out_dir.mkdir(parents=True, exist_ok=True)

        playlist_path = out_dir / "index.m3u8"
        segment_pattern = str(out_dir / "%03d.ts")

  
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-vf",
            f"scale=-2:{cfg['height']}",
            "-c:v",
            "h264",
            "-b:v",
            cfg["video_bitrate"],
            "-c:a",
            "aac",
            "-b:a",
            cfg["audio_bitrate"],
            "-hls_time",
            "6",
            "-hls_list_size",
            "0",
            "-hls_segment_filename",
            segment_pattern,
            str(playlist_path),
        ]

        _run(cmd)
