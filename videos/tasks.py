import subprocess
from pathlib import Path
from django.conf import settings
from .models import Video


RESOLUTIONS = {
    "480p": 480,
    "720p": 720,
    "1080p": 1080,
}


def convert_video_to_hls(video_id: int) -> None:
    """
    Convert uploaded video into HLS format for 480p, 720p and 1080p.
    Output:
        media/hls/<video_id>/<resolution>/index.m3u8
    """

    video = Video.objects.filter(pk=video_id).first()
    if not video or not video.video_file:
        return

    input_path = Path(video.video_file.path)
    if not input_path.exists():
        return

    base_output_dir = Path(settings.MEDIA_ROOT) / "hls" / str(video.id)

    for label, height in RESOLUTIONS.items():
        output_dir = base_output_dir / label
        output_dir.mkdir(parents=True, exist_ok=True)
        playlist_path = output_dir / "index.m3u8"
        segment_pattern = str(output_dir / "%03d.ts")

        cmd = [
            "ffmpeg","-y","-i", str(input_path),
            "-vf", f"scale=-2:{height}",
            "-c:v", "libx264","-c:a", "aac","-hls_time", "6","-hls_list_size", "0",
            "-hls_segment_filename", segment_pattern,str(playlist_path),
        ]

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)