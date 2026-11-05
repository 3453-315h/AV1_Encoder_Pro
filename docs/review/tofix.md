# AV1 Encoder Pro — Remediation & Feature Ledger (v1.2.0)

> Status: Round 1 Fixes, Core Command Builder Unification (`av1core.py`), and ERA Bounded Parameter Search (`era_search.py`) are fully implemented and verified via automated test suites.

## ✅ Completed in Round 1 & Core Unification

1. **CLI `librav1e` & `libaom-av1` Flags:**
   - Dedicated `-qp` and `-speed` for `librav1e`.
   - `-b:v 0` added for `libaom-av1` to enable true unconstrained Constant Quality mode.
2. **Container Audio Compatibility:**
   - Pre-encoding `ffprobe` stream probing.
   - WebM copy safely auto-switches to Opus when stream is incompatible (e.g. AAC) with explicit user notice.
   - Video-only inputs automatically receive `-an`.
3. **Web UI Network Exposure & Concurrency:**
   - Default host bind set to `127.0.0.1` (`HOST` env var opt-in for LAN).
   - `app.queue(default_concurrency_limit=1)` protects against CPU exhaustion.
   - Basic authentication supported via `WEB_USER` and `WEB_PASSWORD`.
   - Docker published port mapped to `127.0.0.1:2081:2081`.
4. **Batch Cancellation & Scheduler Integrity:**
   - `_cancel_requested` check enforced before each file and during FFmpeg subprocess streaming.
   - Cancel during file $N$ halts batch immediately; file $N+1$ never starts.
   - State guards prevent duplicate schedule threads or concurrent batches.
5. **Output Overwrite Safety:**
   - Encodings write to temporary sibling files (`.tmp.<pid>.<ext>`) with atomic `os.replace` on success.
   - Failed or cancelled encodes clean up temporary files, leaving prior good files untouched.
   - `--overwrite` / `-y` flag added to CLI.
   - Batch loop skips `_AV1` files and generates non-colliding suffixes (`_AV1_1`, `_AV1_2`) when target exists.
6. **Encoder Preset Clamping:**
   - Enforced maximum bounds per encoder (`libaom-av1`: 0-8, `librav1e`: 0-10, `libsvtav1`: 0-13).
7. **Docker Compose & CLI Arguments:**
   - Removed redundant `encode_cli.py` argument duplication in `entrypoint.sh`, `docker-compose.yml`, and `DOCKER.md`.
8. **Docker Batch Reporting:**
   - Bash loop aggregates succeeded/failed counts, handles stem collisions across formats, and exits with code 1 on errors.
9. **Scheduler Documentation Alignment:**
   - `USAGE_GUIDE.md` and `README.md` updated to accurately describe in-memory scheduling.
10. **PyInstaller Build Tolerance:**
    - `av1_encoder_ctk.spec` updated to gracefully handle missing local `ffmpeg.exe` and fall back to system `PATH`.
11. **Telemetry & Error Visibility:**
    - Captured circular buffer of last 20-25 lines of stderr; printed upon non-zero exit code.
12. **Shared Engine Unification (`av1core.py`):**
    - Extracted single source of truth for FFmpeg command building, container compatibility, and media probing.
    - CLI, GUI, and Web UI all consume `av1core.py`.
13. **ERA Bounded Parameter Search (`era_search.py`):**
    - Implemented flat PUCT tree search with rank normalization (`rank / (n - 1)`).
    - Multi-objective evaluation of quality (SSIM), compression ratio, and encode speed.
    - Verified with integration test suite.
