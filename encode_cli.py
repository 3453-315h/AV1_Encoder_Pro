#!/usr/bin/env python3
"""
AV1 Encoder Pro - CLI Mode
For headless Docker usage without GUI

Usage:
    python encode_cli.py -i input.mp4 -o output.webm -q 50 -p 6
    python encode_cli.py --help
"""
import subprocess
import argparse
import os
import sys
import collections
import av1core

def get_ffmpeg_path():
    """Find FFmpeg binary"""
    return av1core.get_ffmpeg_path()

def get_ffprobe_path():
    """Find FFprobe binary"""
    return av1core.get_ffprobe_path()

def probe_audio_codec(input_path, ffprobe_path=None):
    """Use ffprobe to check if audio stream exists and return its codec name."""
    return av1core.probe_audio_codec(input_path, ffprobe_path=ffprobe_path)

def build_command(input_path, output_path, quality=50, preset=6,
                  encoder="libsvtav1", audio_codec="libopus", audio_bitrate="128k",
                  resolution=None, tune=0, grain=0, ffmpeg_path=None, ffprobe_path=None):
    """Build FFmpeg command line arguments for encoding."""
    probed = probe_audio_codec(input_path, ffprobe_path=ffprobe_path)
    cmd, notices = av1core.build_ffmpeg_command(
        input_path=input_path,
        output_path=output_path,
        quality=quality,
        preset=preset,
        encoder=encoder,
        audio_codec=audio_codec,
        audio_bitrate=audio_bitrate,
        resolution=resolution,
        tune=tune,
        grain=grain,
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
        probed_audio=probed
    )
    for notice in notices:
        tag = "WARNING" if "clamped" in notice.lower() else "INFO"
        print(f"[{tag}] {notice}")
    return cmd

def encode_video(input_path, output_path, quality=50, preset=6, 
                 encoder="libsvtav1", audio_codec="libopus", audio_bitrate="128k",
                 resolution=None, tune=0, grain=0, overwrite=False):
    """Encode video to AV1 using FFmpeg with safe output handling."""
    if os.path.exists(output_path) and not overwrite:
        print(f"[ERROR] Output file already exists: {output_path}. Use --overwrite or -y to replace.")
        return False

    # Check encoder availability
    available = av1core.get_available_encoders()
    if available and encoder not in available:
        print(f"[ERROR] Encoder '{encoder}' is not supported by your FFmpeg installation.")
        print(f"[INFO] Available AV1 encoders on this system: {', '.join(sorted(available))}")
        return False

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    
    # Write to a temporary sibling file first to prevent partial/corrupted outputs
    out_ext = os.path.splitext(output_path)[1]
    tmp_output = f"{output_path}.tmp.{os.getpid()}{out_ext}"
    
    cmd = build_command(
        input_path, tmp_output, quality=quality, preset=preset,
        encoder=encoder, audio_codec=audio_codec, audio_bitrate=audio_bitrate,
        resolution=resolution, tune=tune, grain=grain
    )
    
    crf = int(round(63 - (quality * 0.63)))
    print(f"[INFO] Input: {input_path}")
    print(f"[INFO] Output: {output_path} (temporary: {tmp_output})")
    print(f"[INFO] Encoder: {encoder}, Quality: {quality}% (CRF {crf}), Preset: {preset}")
    print(f"[CMD] {' '.join(cmd)}")
    print()
    
    stderr_tail = collections.deque(maxlen=25)
    
    try:
        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
        
        for line in process.stderr:
            stderr_tail.append(line.strip())
            if "frame=" in line or "size=" in line or "time=" in line:
                print(f"[PROGRESS] {line.strip()}")
            elif "error" in line.lower():
                print(f"[ERROR] {line.strip()}")
        
        process.wait()
        if process.stderr:
            process.stderr.close()
        
        if process.returncode == 0 and os.path.exists(tmp_output):
            os.replace(tmp_output, output_path)
            print("\n[DONE] Encoding complete!")
            return True
        else:
            if os.path.exists(tmp_output):
                try:
                    os.remove(tmp_output)
                except OSError:
                    pass
            print(f"\n[ERROR] Encoding failed with code {process.returncode}")
            print("[ERROR] FFmpeg diagnostic output (last lines):")
            for err_line in stderr_tail:
                print(f"  {err_line}")
            return False
    except KeyboardInterrupt:
        print("\n[CANCEL] Encoding interrupted by user.")
        if os.path.exists(tmp_output):
            try:
                os.remove(tmp_output)
            except OSError:
                pass
        return False
    except Exception as e:
        print(f"\n[ERROR] Subprocess error: {str(e)}")
        if os.path.exists(tmp_output):
            try:
                os.remove(tmp_output)
            except OSError:
                pass
        return False

def main():
    parser = argparse.ArgumentParser(
        description="AV1 Encoder Pro CLI - Professional AV1 video encoding",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Encode with default settings:
    python encode_cli.py -i video.mp4 -o video_av1.webm

  High quality encoding:
    python encode_cli.py -i video.mp4 -o video_av1.mp4 -q 80 -p 4

  Fast encoding for web:
    python encode_cli.py -i video.mp4 -o video_av1.webm -q 40 -p 10 -r 720p

  Film with grain:
    python encode_cli.py -i movie.mp4 -o movie_av1.mp4 -q 60 -g 15
        """
    )
    
    parser.add_argument("-v", "--version", action="version", version=f"AV1 Encoder Pro {av1core.__version__}")
    parser.add_argument("-i", "--input", required=True, help="Input video file path")
    parser.add_argument("-o", "--output", required=True, help="Output video file path")
    parser.add_argument("-q", "--quality", type=int, default=50, 
                        help="Quality 0-100 (default: 50, maps to CRF 0-63)")
    parser.add_argument("-p", "--preset", type=int, default=6, choices=range(0, 14),
                        help="Speed preset 0-13 (default: 6, lower=slower/better)")
    parser.add_argument("-e", "--encoder", default="libsvtav1",
                        choices=["libsvtav1", "libaom-av1", "librav1e", "av1_nvenc", "av1_amf", "av1_qsv"],
                        help="AV1 encoder to use (default: libsvtav1)")
    parser.add_argument("-a", "--audio", default="libopus",
                        choices=["libopus", "aac", "copy", "none"],
                        help="Audio codec (default: libopus)")
    parser.add_argument("-b", "--bitrate", default="128k",
                        help="Audio bitrate (default: 128k)")
    parser.add_argument("-r", "--resolution", default=None,
                        choices=["4k", "1080p", "720p", "480p"],
                        help="Output resolution (default: original)")
    parser.add_argument("-t", "--tune", type=int, default=0, choices=[0, 1, 2],
                        help="Tune: 0=VQ, 1=PSNR, 2=SSIM (default: 0)")
    parser.add_argument("-g", "--grain", type=int, default=0,
                        help="Film grain 0-50 (default: 0, SVT-AV1 only)")
    parser.add_argument("-y", "--overwrite", action="store_true", default=False,
                        help="Overwrite output file if it already exists")
    
    args = parser.parse_args()
    
    # Range validations
    if args.quality < 0 or args.quality > 100:
        print(f"[ERROR] Quality must be between 0 and 100, got {args.quality}")
        sys.exit(1)
        
    if args.grain < 0 or args.grain > 50:
        print(f"[ERROR] Film grain must be between 0 and 50, got {args.grain}")
        sys.exit(1)
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"[ERROR] Input file not found: {args.input}")
        sys.exit(1)
    
    success = encode_video(
        args.input,
        args.output,
        quality=args.quality,
        preset=args.preset,
        encoder=args.encoder,
        audio_codec=args.audio,
        audio_bitrate=args.bitrate,
        resolution=args.resolution,
        tune=args.tune,
        grain=args.grain,
        overwrite=args.overwrite
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
