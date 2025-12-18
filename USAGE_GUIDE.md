# AV1 Video Encoder Pro - Usage Guide

## Quick Start

### Running the Application

**Windows Executable:**

```
Double-click AV1_Encoder_Pro.exe
```

**From Source:**

```bash
python av1_encoder_ctk.py
```

## Video Encoder Tab

The main encoding interface for single video files.

### Basic Workflow

1. **Select Input Video**
   - Click **Browse** next to "Input File"
   - Or **drag and drop** a video file directly onto the app window

2. **Set Output Path**
   - The output path is auto-generated based on input file
   - Format: `{original_name}_AV1.{extension}`
   - Click **Browse** to change the output location

3. **Adjust Quality Settings**
   - **Quality Slider** (0-100%): Higher = better quality, larger file
     - 50% (CRF 30) recommended for general use
   - **Speed Preset** (0-13): Lower = slower but better compression
     - Preset 6 is balanced
   - **Tune Mode**:
     - VQ (Visual Quality) - Optimized for human perception
     - PSNR - Optimized for peak signal-to-noise ratio
     - SSIM - Optimized for structural similarity

4. **Configure Audio**
   - **Copy** - Keep original audio (fastest)
   - **Opus 128k/192k/320k** - Re-encode to Opus (recommended for WebM)
   - **AAC 128k/192k/320k** - Re-encode to AAC (for MP4 compatibility)
   - **No Audio** - Remove audio track

5. **Additional Options**
   - **Container Format**: WebM (recommended) or MP4
   - **Resolution**: Original, 4K, 1080p, 720p, or 480p
   - **Film Grain**: Add synthetic film grain (0-50)
   - **Two-Pass**: Enable for better quality (slower)

6. **Start Encoding**
   - Click **Encode Video**
   - Progress appears in the console area
   - Click **Cancel** to stop encoding

---

## Batch Processing Tab

Process multiple videos at once.

### Adding Files

**Method 1: Drag & Drop Folder**

1. Navigate to the **Batch Processing** tab
2. Drag a folder from File Explorer onto the file list area
3. All video files in the folder will be added automatically

**Method 2: Add Folder Button**

1. Click **Add Folder**
2. Select a folder containing videos
3. Video files will be scanned and added

**Method 3: Add Individual Files** (if available)

1. Click **Add Files** (if the button exists)
2. Select multiple video files

### Batch Settings

- **Save to Folder**: Set a custom output directory for all encoded files
- **Click Browse** next to the folder field to choose destination

### Running the Batch

1. Verify the file list shows all videos
2. Encoding settings from the Video Encoder tab will be used
3. Click **Start Batch**
4. Progress appears in the console for each file
5. Click **Clear** to remove all files from the queue

### Supported Video Formats

- MP4, MKV, AVI, MOV, WebM, WMV, FLV

---

## Scheduler Tab

Schedule encoding tasks for later execution.

### Creating a Scheduled Task

1. **Select Folder** - Choose a folder with videos to encode
2. **Set Date/Time** - Pick when encoding should start
3. **Click Add to Schedule**

### Managing Tasks

- View all scheduled tasks in the task list
- **Run Now** - Start task immediately
- **Cancel** - Remove task from schedule

---

## Console/Log Area

The bottom section shows real-time encoding output:

- **[INFO]** - General information
- **[ENCODE]** - FFmpeg encoding progress
- **[ERROR]** - Error messages
- **[BATCH]** - Batch processing progress

---

## Tips & Best Practices

### Quality vs. Speed Tradeoffs

| Use Case | CRF | Preset | Notes |
|----------|-----|--------|-------|
| Archival | 20-25 | 4 | Best quality, slow |
| General | 28-32 | 6 | Good balance |
| Web/Streaming | 35-40 | 8 | Smaller files |
| Quick Preview | 40-50 | 10 | Fastest |

### Container Format Selection

- **WebM**: Best for web, smaller files, Opus audio
- **MP4**: Maximum compatibility, AAC audio

### Film Grain

- Use film grain (5-15) to reduce banding in gradients
- Higher values (20-50) add artistic effect
- Increases file size slightly

### Two-Pass Encoding

- Produces more consistent quality
- Takes approximately 2x longer
- Recommended for final exports

---

## Troubleshooting

### "FFmpeg not found"

- Ensure `ffmpeg.exe` is in the same folder as the app
- Or install FFmpeg system-wide and add to PATH

### Window doesn't appear

- Check the Windows taskbar for the app icon
- Try running from command line to see errors:

  ```bash
  python av1_encoder_ctk.py
  ```

### Encoding fails

- Check the console for error messages
- Verify input file is a valid video
- Ensure sufficient disk space for output

### Drag & drop not working

- Make sure `windnd` package is installed:

  ```bash
  pip install windnd
  ```

---

## Keyboard Shortcuts

(To be implemented in future versions)

---

## Technical Details

### Encoding Command

The app generates FFmpeg commands like:

```bash
ffmpeg -i input.mp4 -c:v libsvtav1 -crf 30 -preset 6 -svtav1-params tune=0 -c:a libopus -b:a 128k output.webm
```

### Dependencies

- **FFmpeg** with libsvtav1 encoder
- **CustomTkinter** for the modern dark UI
- **Pillow** for image handling
- **windnd** for Windows drag & drop
