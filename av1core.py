"""
AV1 Encoder Pro - Core Engine
Shared encoder logic, command builders, and media probing utilities.
"""
import os
import subprocess
import shutil

__version__ = "1.3.0"

SUPPORTED_ENCODERS = [
    "libsvtav1",
    "libaom-av1",
    "librav1e",
    "av1_nvenc",
    "av1_amf",
    "av1_qsv",
]

GPU_ENCODERS = {"av1_nvenc", "av1_amf", "av1_qsv"}

WEBM_COMPATIBLE_AUDIO = {"opus", "vorbis", "flac"}

_CACHED_AVAILABLE_ENCODERS = None


def get_available_encoders(ffmpeg_path: str = None) -> set:
    """Query local ffmpeg -encoders to determine which AV1 encoders are installed."""
    global _CACHED_AVAILABLE_ENCODERS
    if _CACHED_AVAILABLE_ENCODERS is not None:
        return _CACHED_AVAILABLE_ENCODERS

    if ffmpeg_path is None:
        ffmpeg_path = get_ffmpeg_path()
    try:
        cmd = [ffmpeg_path, "-encoders"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        found = set()
        for line in res.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2:
                codec_name = parts[1]
                if codec_name in SUPPORTED_ENCODERS:
                    found.add(codec_name)
        _CACHED_AVAILABLE_ENCODERS = found
        return found
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return set()

RESOLUTION_MAP = {
    "4k": "3840:2160",
    "1080p": "1920:1080",
    "720p": "1280:720",
    "480p": "854:480",
}


def quality_to_crf(quality: int) -> int:
    """Map 0-100 quality percentage to 0-63 CRF scale."""
    clamped_q = max(0, min(100, int(quality)))
    return int(round(63 - (clamped_q * 0.63)))


def clamp_preset(encoder: str, preset: int | str) -> int:
    """Clamp preset to valid ranges accepted by specific encoder."""
    try:
        p = int(preset)
    except (ValueError, TypeError):
        p = 6

    if encoder == "libaom-av1":
        return max(0, min(8, p))
    elif encoder == "librav1e":
        return max(0, min(10, p))
    elif encoder == "libsvtav1":
        return max(0, min(13, p))
    return max(0, p)


def get_ffmpeg_path() -> str:
    """Locate ffmpeg binary via environment or system PATH."""
    return os.environ.get("FFMPEG_PATH", "ffmpeg")


def get_ffprobe_path() -> str:
    """Locate ffprobe binary via environment or system PATH."""
    return os.environ.get("FFPROBE_PATH", "ffprobe")


def probe_audio_codec(input_path: str, ffprobe_path: str = None) -> str | None:
    """Probe the first audio stream codec name with ffprobe."""
    if ffprobe_path is None:
        ffprobe_path = get_ffprobe_path()
    try:
        cmd = [
            ffprobe_path, "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_name",
            "-of", "csv=p=0",
            input_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        codec = res.stdout.strip().lower()
        return codec if codec else None
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None


def probe_video_duration(input_path: str, ffprobe_path: str = None) -> float | None:
    """Probe video duration in seconds."""
    if ffprobe_path is None:
        ffprobe_path = get_ffprobe_path()
    try:
        cmd = [
            ffprobe_path, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            input_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        val = res.stdout.strip()
        return float(val) if val else None
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired, ValueError):
        return None


def resolve_audio_args(input_path: str, output_path: str, audio_codec: str,
                       audio_bitrate: str = "128k", ffprobe_path: str = None,
                       probed_codec: str = None) -> tuple[list[str], str | None]:
    """
    Resolve audio arguments and return (args_list, notice_message).
    Guards WebM containers against unsupported codecs (e.g. AAC) during copy.
    """
    out_ext = os.path.splitext(output_path)[1].lower()
    is_webm = out_ext == ".webm"
    if probed_codec is not None:
        src_codec = probed_codec.lower() if probed_codec else None
    else:
        src_codec = probe_audio_codec(input_path, ffprobe_path=ffprobe_path)

    if src_codec is None or audio_codec == "none":
        return (["-an"], None)

    if audio_codec == "copy":
        if is_webm and src_codec not in WEBM_COMPATIBLE_AUDIO:
            notice = f"Audio codec '{src_codec}' is not supported in WebM container; converting to Opus 128k"
            return (["-c:a", "libopus", "-b:a", "128k"], notice)
        return (["-c:a", "copy"], None)

    if audio_codec == "aac":
        if is_webm:
            notice = f"AAC audio is not supported in WebM container; converting to Opus {audio_bitrate}"
            return (["-c:a", "libopus", "-b:a", audio_bitrate], notice)
        return (["-c:a", "aac", "-b:a", audio_bitrate], None)

    return (["-c:a", audio_codec, "-b:a", audio_bitrate], None)


def build_ffmpeg_command(input_path: str, output_path: str, quality: int = 50,
                         preset: int = 6, encoder: str = "libsvtav1",
                         audio_codec: str = "libopus", audio_bitrate: str = "128k",
                         resolution: str = None, tune: int | str = 0, grain: int = 0,
                         threads: int = 0, ffmpeg_path: str = None,
                         ffprobe_path: str = None, probed_audio: str = None) -> tuple[list[str], list[str]]:
    """
    Build the complete FFmpeg argument list.
    Returns (cmd_list, notices_list).
    """
    if ffmpeg_path is None:
        ffmpeg_path = get_ffmpeg_path()

    notices = []
    crf = quality_to_crf(quality)
    clamped_preset = clamp_preset(encoder, preset)

    try:
        raw_p = int(preset)
        if raw_p != clamped_preset:
            notices.append(f"{encoder} preset clamped from {raw_p} to {clamped_preset}")
    except (ValueError, TypeError):
        pass

    cmd = [ffmpeg_path, "-y", "-i", input_path]

    # Video Encoder options
    if encoder == "libsvtav1":
        svt_params = f"tune={tune}"
        if grain > 0:
            svt_params += f":film-grain={grain}:film-grain-denoise=1"
        if threads > 0:
            svt_params += f":logical-processors={threads}"
        cmd.extend(["-c:v", encoder, "-crf", str(crf), "-preset", str(clamped_preset), "-svtav1-params", svt_params])
    elif encoder == "librav1e":
        cmd.extend(["-c:v", encoder, "-qp", str(crf), "-speed", str(clamped_preset)])
    elif encoder == "libaom-av1":
        cmd.extend(["-c:v", encoder, "-crf", str(crf), "-b:v", "0", "-cpu-used", str(clamped_preset)])
        if threads > 0:
            cmd.extend(["-threads", str(threads)])
    elif encoder in GPU_ENCODERS:
        gpu_crf = min(51, crf)
        cmd.extend(["-c:v", encoder])
        if encoder == "av1_nvenc":
            cmd.extend(["-cq", str(gpu_crf), "-preset", "p" + str(min(7, max(1, 8 - clamped_preset)))])
        elif encoder == "av1_amf":
            cmd.extend(["-rc", "cqp", "-qp_i", str(gpu_crf), "-qp_p", str(gpu_crf)])
        elif encoder == "av1_qsv":
            cmd.extend(["-global_quality", str(max(1, gpu_crf))])
    else:
        cmd.extend(["-c:v", encoder, "-crf", str(crf), "-b:v", "0", "-cpu-used", str(clamped_preset)])

    # Resolution scaling
    if resolution:
        clean_res = resolution.lower().split()[0].replace("(", "").replace(")", "")
        if clean_res in RESOLUTION_MAP:
            cmd.extend(["-vf", f"scale={RESOLUTION_MAP[clean_res]}:flags=lanczos"])

    # Audio options
    audio_args, audio_notice = resolve_audio_args(
        input_path, output_path, audio_codec, audio_bitrate,
        ffprobe_path=ffprobe_path, probed_codec=probed_audio
    )
    if audio_notice:
        notices.append(audio_notice)
    cmd.extend(audio_args)

    cmd.append(output_path)
    return cmd, notices
