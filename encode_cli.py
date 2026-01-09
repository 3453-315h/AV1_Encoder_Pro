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

def get_ffmpeg_path():
    """Find FFmpeg binary"""
    return "ffmpeg"

def encode_video(input_path, output_path, quality=50, preset=6, 
                 encoder="libsvtav1", audio_codec="libopus", audio_bitrate="128k",
                 resolution=None, tune=0, grain=0):
    """Encode video to AV1 using FFmpeg"""
    
    # Calculate CRF from quality percentage
    crf = int(63 - (quality * 0.63))
    
    # Build command
    cmd = ["ffmpeg", "-y", "-i", input_path]
    
    # Video encoding options
    if encoder == "libsvtav1":
        svt_params = f"tune={tune}"
        if grain > 0:
            svt_params += f":film-grain={grain}:film-grain-denoise=1"
        cmd.extend(["-c:v", encoder, "-crf", str(crf), "-preset", str(preset), "-svtav1-params", svt_params])
    else:
        cmd.extend(["-c:v", encoder, "-crf", str(crf), "-cpu-used", str(preset)])
    
    # Resolution scaling
    if resolution:
        res_map = {
            "4k": "3840:2160",
            "1080p": "1920:1080",
            "720p": "1280:720",
            "480p": "854:480"
        }
        if resolution.lower() in res_map:
            cmd.extend(["-vf", f"scale={res_map[resolution.lower()]}:flags=lanczos"])
    
    # Audio options
    if audio_codec == "none":
        cmd.append("-an")
    elif audio_codec == "copy":
        cmd.extend(["-c:a", "copy"])
    else:
        cmd.extend(["-c:a", audio_codec, "-b:a", audio_bitrate])
    
    cmd.append(output_path)
    
    print(f"[INFO] Input: {input_path}")
    print(f"[INFO] Output: {output_path}")
    print(f"[INFO] Encoder: {encoder}, CRF: {crf}, Preset: {preset}")
    print(f"[CMD] {' '.join(cmd)}")
    print()
    
    # Run FFmpeg
    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
    
    for line in process.stderr:
        if "frame=" in line or "size=" in line or "time=" in line:
            print(f"[PROGRESS] {line.strip()}")
        elif "error" in line.lower():
            print(f"[ERROR] {line.strip()}")
    
    process.wait()
    
    if process.returncode == 0:
        print("\n[DONE] Encoding complete!")
        return True
    else:
        print(f"\n[ERROR] Encoding failed with code {process.returncode}")
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
    
    parser.add_argument("-i", "--input", required=True, help="Input video file path")
    parser.add_argument("-o", "--output", required=True, help="Output video file path")
    parser.add_argument("-q", "--quality", type=int, default=50, 
                        help="Quality 0-100 (default: 50, maps to CRF)")
    parser.add_argument("-p", "--preset", type=int, default=6, choices=range(0, 14),
                        help="Speed preset 0-13 (default: 6, lower=slower/better)")
    parser.add_argument("-e", "--encoder", default="libsvtav1",
                        choices=["libsvtav1", "libaom-av1", "librav1e"],
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
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"[ERROR] Input file not found: {args.input}")
        sys.exit(1)
    
    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
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
        grain=args.grain
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
