#!/usr/bin/env python3
"""
AV1 Encoder Pro - Web Interface
Browser-based UI for AV1 video encoding via Gradio.
"""

import gradio as gr
import subprocess
import os
import sys
import re
from pathlib import Path
from datetime import datetime
import av1core


# Constants
ENCODERS = av1core.SUPPORTED_ENCODERS
CLI_SCRIPT = os.environ.get("CLI_PATH", str(Path(__file__).parent / "encode_cli.py"))
AUDIO_CODECS = ["libopus", "aac", "copy", "none"]
RESOLUTIONS = ["original", "4k", "1080p", "720p", "480p"]
TUNE_OPTIONS = ["VQ (Visual Quality)", "PSNR", "SSIM"]
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/output" if os.path.exists("/output") else "./output"))
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/videos" if os.path.exists("/videos") else "./videos"))


def encode_video(
    input_file,
    quality: int,
    preset: int,
    encoder: str,
    audio_codec: str,
    audio_bitrate: str,
    resolution: str,
    tune: str,
    film_grain: int,
    output_format: str,
    progress=gr.Progress()
):
    """Encode video using the CLI encoder."""
    
    if input_file is None:
        return None, "❌ Please upload a video file first."

    # Validate encoder availability
    available = av1core.get_available_encoders()
    if available and encoder not in available:
        return None, f"❌ Encoder '{encoder}' is not supported by the server's FFmpeg.\nAvailable encoders: {', '.join(sorted(available))}"
    
    try:
        # Ensure output directory exists
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Get input file path
        input_path = Path(input_file)
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"{input_path.stem}_{timestamp}_av1.{output_format}"
        output_path = OUTPUT_DIR / output_name
        
        # Map tune selection to value
        tune_map = {"VQ (Visual Quality)": 0, "PSNR": 1, "SSIM": 2}
        tune_value = tune_map.get(tune, 0)
        
        # Build command
        cmd = [
            sys.executable, CLI_SCRIPT,
            "-i", str(input_path),
            "-o", str(output_path),
            "-q", str(quality),
            "-p", str(preset),
            "-e", encoder,
            "-a", audio_codec,
            "-b", audio_bitrate,
            "-t", str(tune_value),
            "-g", str(film_grain),
            "-y"
        ]
        
        if resolution != "original":
            cmd.extend(["-r", resolution])
        
        total_duration = av1core.probe_video_duration(str(input_path))
        progress(0.1, desc="Starting encode...")
        
        # Run encoding
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        log_output = []
        progress(0.15, desc="Encoding in progress...")
        
        for line in process.stdout:
            line_str = line.strip()
            log_output.append(line_str)
            # Parse real progress from ffmpeg time= output if available
            if "time=" in line_str:
                match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line_str)
                if match and total_duration and total_duration > 0:
                    hours, mins, secs = int(match.group(1)), int(match.group(2)), float(match.group(3))
                    cur_secs = hours * 3600 + mins * 60 + secs
                    fraction = min(0.95, max(0.15, cur_secs / total_duration))
                    progress(fraction, desc=f"Encoding: {int(fraction * 100)}% ({cur_secs:.1f}s / {total_duration:.1f}s)...")
                else:
                    progress(0.5, desc=f"Encoding: {line_str[:50]}...")
            elif "frame=" in line_str:
                progress(0.3, desc=f"Encoding: {line_str[:50]}...")
        
        process.wait()
        progress(0.9, desc="Finalizing...")
        
        if process.returncode == 0 and output_path.exists():
            file_size = output_path.stat().st_size / (1024 * 1024)
            progress(1.0, desc="Complete!")
            return str(output_path), f"✅ Encoding complete!\n📁 Output: {output_name}\n📊 Size: {file_size:.2f} MB"
        else:
            error_log = "\n".join(log_output[-20:])
            return None, f"❌ Encoding failed!\n\nLog:\n{error_log}"
            
    except Exception as e:
        return None, f"❌ Error: {str(e)}"


def get_file_info(file):
    """Get information about uploaded file."""
    if file is None:
        return "No file uploaded"
    
    try:
        path = Path(file)
        size_mb = path.stat().st_size / (1024 * 1024)
        
        # Try to get video info with ffprobe
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,duration,codec_name",
             "-of", "csv=p=0", str(path)],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(",")
            if len(parts) >= 3:
                codec = parts[0] if len(parts) > 0 else "unknown"
                width = parts[1] if len(parts) > 1 else "?"
                height = parts[2] if len(parts) > 2 else "?"
                duration = float(parts[3]) if len(parts) > 3 and parts[3] else 0
                
                mins = int(duration // 60)
                secs = int(duration % 60)
                
                return f"""📹 **{path.name}**
• Size: {size_mb:.2f} MB
• Resolution: {width}x{height}
• Codec: {codec}
• Duration: {mins}m {secs}s"""
        
        return f"""📹 **{path.name}**
• Size: {size_mb:.2f} MB"""
        
    except Exception as e:
        return f"Error reading file: {e}"


# Create Gradio Interface
with gr.Blocks(
    title="AV1 Encoder Pro",
    theme=gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="slate",
    ),
    css="""
    .gradio-container { max-width: 1200px !important; }
    .header { text-align: center; margin-bottom: 1rem; }
    .header h1 { color: #2563eb; margin-bottom: 0.5rem; }
    """
) as app:
    
    gr.HTML("""
    <div class="header">
        <h1>🎬 AV1 Encoder Pro</h1>
        <p>Professional AV1 video encoding in your browser</p>
    </div>
    """)
    
    with gr.Row():
        # Left column - Input
        with gr.Column(scale=1):
            gr.Markdown("### 📤 Input")
            
            input_video = gr.File(
                label="Upload Video",
                file_types=["video"],
                type="filepath"
            )
            
            file_info = gr.Markdown("No file uploaded")
            input_video.change(get_file_info, input_video, file_info)
        
        # Right column - Settings
        with gr.Column(scale=2):
            gr.Markdown("### ⚙️ Encoding Settings")
            
            with gr.Row():
                quality = gr.Slider(
                    minimum=0, maximum=100, value=50, step=1,
                    label="Quality (0-100)",
                    info="Higher = better quality, larger file"
                )
                preset = gr.Slider(
                    minimum=0, maximum=13, value=6, step=1,
                    label="Speed Preset (0-13)",
                    info="Lower = slower, better compression"
                )
            
            with gr.Row():
                encoder = gr.Dropdown(
                    choices=ENCODERS,
                    value="libsvtav1",
                    label="Encoder",
                    info="SVT-AV1 recommended for best speed/quality"
                )
                resolution = gr.Dropdown(
                    choices=RESOLUTIONS,
                    value="original",
                    label="Output Resolution"
                )
            
            with gr.Row():
                audio_codec = gr.Dropdown(
                    choices=AUDIO_CODECS,
                    value="libopus",
                    label="Audio Codec"
                )
                audio_bitrate = gr.Dropdown(
                    choices=["64k", "96k", "128k", "192k", "256k", "320k"],
                    value="128k",
                    label="Audio Bitrate"
                )
            
            with gr.Accordion("Advanced Options", open=False):
                with gr.Row():
                    tune = gr.Dropdown(
                        choices=TUNE_OPTIONS,
                        value="VQ (Visual Quality)",
                        label="Tune Mode"
                    )
                    film_grain = gr.Slider(
                        minimum=0, maximum=50, value=0, step=1,
                        label="Film Grain Synthesis",
                        info="Add artificial film grain (0 = off)"
                    )
                
                output_format = gr.Radio(
                    choices=["webm", "mp4", "mkv"],
                    value="webm",
                    label="Output Format"
                )
    
    gr.Markdown("---")
    
    with gr.Row():
        encode_btn = gr.Button("🚀 Start Encoding", variant="primary", size="lg")
    
    with gr.Row():
        with gr.Column():
            status_output = gr.Markdown("Ready to encode...")
        with gr.Column():
            output_file = gr.File(label="📥 Download Encoded Video")
    
    # Connect encoding function
    encode_btn.click(
        fn=encode_video,
        inputs=[
            input_video, quality, preset, encoder,
            audio_codec, audio_bitrate, resolution,
            tune, film_grain, output_format
        ],
        outputs=[output_file, status_output]
    )
    
    gr.Markdown("""
    ---
    ### 📖 Quick Guide
    
    | Quality | CRF Range | Best For |
    |---------|-----------|----------|
    | 70-100 | 18-23 | Archival, professional |
    | 40-69 | 24-37 | General use |
    | 20-39 | 38-50 | Web streaming |
    
    **Tips:**
    - **SVT-AV1** offers the best speed/quality balance
    - Lower **preset** = better compression but slower
    - **WebM** format has broadest browser support
    """)


if __name__ == "__main__":
    server_name = os.environ.get("HOST", "127.0.0.1")
    server_port = int(os.environ.get("PORT", "2081"))
    
    auth = None
    web_user = os.environ.get("WEB_USER")
    web_pass = os.environ.get("WEB_PASSWORD")
    if web_user and web_pass:
        auth = (web_user, web_pass)
        
    app.queue(default_concurrency_limit=1)
    
    app.launch(
        server_name=server_name,
        server_port=server_port,
        auth=auth,
        share=False,
        show_error=True
    )
