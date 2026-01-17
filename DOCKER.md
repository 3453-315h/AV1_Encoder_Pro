# AV1 Encoder Pro - Docker Usage Guide

Docker containerization for professional AV1 video encoding.

## Quick Start

### Build the Image

```bash
docker build -t av1-encoder-pro .
```

### CLI Mode (Recommended)

Encode a single video:
```bash
docker run -v $(pwd)/videos:/videos -v $(pwd)/output:/output av1-encoder-pro \
    encode_cli.py -i /videos/input.mp4 -o /output/output.webm -q 50 -p 6
```

Show help:
```bash
docker run av1-encoder-pro encode_cli.py --help
```

---

## Using Docker Compose

### Setup

1. Create input/output directories:
```bash
mkdir -p videos output
```

2. Place your video files in the `videos/` folder

### Encode Single Video

```bash
docker-compose run encoder encode_cli.py -i /videos/myvideo.mp4 -o /output/myvideo_av1.webm
```

### Batch Encode All Videos

```bash
docker-compose run batch
```

This encodes all videos in `./videos/` to `./output/` with default settings.

### Web UI Mode (Recommended for Windows/macOS)

Access the encoder via your web browser:

```bash
docker-compose up web
```

Then open **http://localhost:2081** in your browser.

Features:
- Upload videos directly in browser
- Configure all encoding settings
- Download encoded files
- Works on **all platforms** (Windows, macOS, Linux)

### GUI Mode (Linux Only)

```bash
# Allow Docker to access X11 display
xhost +local:docker

# Start GUI
docker-compose up gui
```

---

## CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `-i, --input` | Input video path | (required) |
| `-o, --output` | Output video path | (required) |
| `-q, --quality` | Quality 0-100 | 50 |
| `-p, --preset` | Speed 0-13 (lower=better) | 6 |
| `-e, --encoder` | libsvtav1, libaom-av1, librav1e | libsvtav1 |
| `-a, --audio` | libopus, aac, copy, none | libopus |
| `-b, --bitrate` | Audio bitrate | 128k |
| `-r, --resolution` | 4k, 1080p, 720p, 480p | original |
| `-t, --tune` | 0=VQ, 1=PSNR, 2=SSIM | 0 |
| `-g, --grain` | Film grain 0-50 | 0 |

---

## Examples

### High Quality Archival
```bash
docker run -v $(pwd):/data av1-encoder-pro \
    encode_cli.py -i /data/movie.mkv -o /data/movie_archive.webm \
    -q 80 -p 2 -e libsvtav1 -a libopus -b 192k
```

### Fast Web Encode
```bash
docker run -v $(pwd):/data av1-encoder-pro \
    encode_cli.py -i /data/video.mp4 -o /data/video_web.webm \
    -q 40 -p 10 -r 720p
```

### Film with Grain
```bash
docker run -v $(pwd):/data av1-encoder-pro \
    encode_cli.py -i /data/film.mp4 -o /data/film_av1.mp4 \
    -q 60 -p 4 -g 15 -t 0
```

---

## Quality Reference

| Quality % | CRF | Use Case |
|-----------|-----|----------|
| 70-100 | 18-23 | Archival, professional |
| 40-69 | 24-37 | General use |
| 20-39 | 38-50 | Web streaming |
| 0-19 | 51-63 | Bandwidth-limited |

---

## Notes

- **FFmpeg**: Container uses system FFmpeg with full AV1 codec support
- **Encoders**: SVT-AV1 (recommended), libaom, rav1e available
- **GPU**: GPU encoders (NVENC, AMF, QSV) require NVIDIA Container Toolkit
- **GUI**: Only works on Linux with X11 display forwarding

---

## Deploy to Docker Hub

To share your encoder image on Docker Hub:

1.  **Login to Docker Hub**
    ```bash
    docker login
    ```

2.  **Tag the Image**
    Replace `your-username` with your actual Docker Hub username.
    ```bash
    docker tag av1-encoder-pro your-username/av1-encoder-pro:v1.0.0
    docker tag av1-encoder-pro your-username/av1-encoder-pro:latest
    ```

3.  **Push to Docker Hub**
    ```bash
    docker push your-username/av1-encoder-pro:v1.0.0
    docker push your-username/av1-encoder-pro:latest
    ```

---

## Unraid Setup Guide

You can install this container on Unraid using the **Docker** tab > **Add Container** button.

### Manual Configuration

Fill in the "Add Container" form with these values:

| Field | Value | Notes |
|-------|-------|-------|
| **Name** | `AV1-Encoder-Pro` | |
| **Repository** | `315h/av1-encoder-pro:latest` | **Replace** `your-username` with your Docker Hub ID |
| **Network Type** | `Bridge` | |
| **Console Shell Command** | `Shell` | |
| **Privileged** | `Off` | Turn ON if you need extensive hardware access (rare) |
| **WebUI** | `http://[IP]:[PORT:2081]/` | Enables the "WebUI" context menu item |

### Port Mappings (Add Port)

| Config | Value |
|--------|-------|
| **Container Port** | `2081` |
| **Host Port** | `2081` |
| **Connection Type** | `TCP` |

### Path Mappings (Add Path)

You need two paths: one for your source videos and one for output.

**1. Input Videos**
- **Container Path**: `/videos`
- **Host Path**: `/mnt/user/Isos/Source` (or wherever your videos are)
- **Access Mode**: `Read/Write` (or Read Only if you prefer)

**2. Output Directory**
- **Container Path**: `/output`
- **Host Path**: `/mnt/user/Isos/Converted`
- **Access Mode**: `Read/Write`

### GPU Passthrough (NVIDIA)

To use NVENC hardware encoding or acceleration:

1.  **Install the "Nvidia Driver" Plugin**:
    - Go to the **Apps** tab in Unraid.
    - Search for and install **"Nvidia Driver"**.
    - Go to **Settings > Nvidia Driver** and download the latest driver version. Reboot if required.

2.  **Configure the Container**:
    - Build your container image (if building locally) or pull it.
    - Go to the **Docker** tab and edit the `AV1-Encoder-Pro` container.
    - Toggle **Advanced View** to ON (switch in the top right corner).
    - Find the **Extra Parameters** field and add:
      ```text
      --runtime=nvidia
      ```
    - Add a **Variable** (Click "Add another Path, Port, Variable..."):
        - **Config Type**: `Variable`
        - **Name**: `NVIDIA_VISIBLE_DEVICES`
        - **Key**: `NVIDIA_VISIBLE_DEVICES`
        - **Value**: `all` (or the specific UUID of your GPU)
    - Add another **Variable**:
        - **Config Type**: `Variable`
        - **Name**: `NVIDIA_DRIVER_CAPABILITIES`
        - **Key**: `NVIDIA_DRIVER_CAPABILITIES`
        - **Value**: `all`

3.  **Verify**:
    - Start the container.
    - Open the Web UI console or docker shell.
    - Run `nvidia-smi` to confirm the GPU is visible.


---


