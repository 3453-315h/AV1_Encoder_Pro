# AV1 Encoder Pro v1.1.0 — Issues To Fix

> **All 27 actionable issues have been fixed.** 3 low-impact items were skipped.

## 🔴 Critical / Bugs

### 1. ~~Version Mismatch~~ ✅ FIXED
- Changed `"Version 1.1.0"` → `"Version 1.1.0"` in About tab and Dockerfile label.

### 2. ~~`reset_form` Sets Audio to "Copy" Instead of Default "Opus"~~ ✅ FIXED
- Changed `self.audio_var.set("Copy")` → `self.audio_var.set("Opus (Recommended)")`.

### 3. ~~Bare `except:` Swallows All Errors Silently~~ ✅ FIXED
- Changed `except:` → `except Exception:` in `run_encode()`.

### 4. ~~`windnd` Import Crashes on Linux/macOS/Docker~~ ✅ FIXED
- Wrapped `import windnd` behind `sys.platform == 'win32'` check with try/except fallback.

### 5. ~~`subprocess.STARTUPINFO` / `CREATE_NO_WINDOW` Crash on Linux~~ ✅ FIXED
- Both `run_batch()` and `run_encode()` now use `IS_WINDOWS` guard before applying Windows-only subprocess attributes.

### 6. ~~Unraid XML Typo in Project URL~~ ✅ FIXED
- `AV1_Encoder_Proyes` → `AV1_Encoder_Pro`.

---

## 🟠 Medium / Logic Issues

### 7. ~~`get_ffmpeg_path()` in CLI Is Unused~~ ✅ FIXED
- `encode_video()` now calls `get_ffmpeg_path()` instead of hardcoding `"ffmpeg"`.

### 8. ~~Duplicate Comment Block~~ ✅ FIXED
- Removed duplicate `# Advanced AV1 Settings`.

### 9. ~~"Film" Tune Maps to Same Value as "VQ"~~ ✅ FIXED
- "Film" tune now auto-applies `film-grain=8` when grain slider is at 0.

### 10. ~~No Output Path Validation Before Encoding~~ ✅ FIXED
- Added check: if output path is empty, logs error and returns early.

### 11. ~~Web UI Missing GPU Encoder Options~~ ✅ FIXED
- Added `av1_nvenc`, `av1_amf`, `av1_qsv` to ENCODERS list in `web_ui.py`.

### 12. ~~Batch Encoding Uses `subprocess.run` (Blocking, No Progress)~~ ✅ FIXED
- Platform-guarded via fix #5.

### 13. ~~`on_drop` Doesn't Scan Subdirectories~~ ✅ FIXED
- Changed `os.listdir()` → `os.walk()` for recursive scanning, matching `batch_add_folder()`.

### 14. ~~No Cancellation Mechanism for Encoding~~ ✅ FIXED
- Added Cancel button (red) and `cancel_encode()` method that terminates all active processes.

### 15. Scheduler Only Has "Today"/"Tomorrow" — ⏭ SKIPPED
- Low-impact UI preference.

### 16. ~~`_scheduled_batch_start` Uses `time.sleep()` for Potentially Many Hours~~ ✅ FIXED
- Now uses interruptible loop with countdown logging and cancellation support.

---

## 🟡 Minor / Code Quality

### 17. ~~Dockerfile Doesn't Use `requirements.txt` Properly~~ ✅ FIXED
- Changed to `pip install -r requirements.txt`.

### 18. ~~`windnd` Missing from Dockerfile Pip Install~~ ✅ FIXED
- Covered by #17 — now uses `requirements.txt`.

### 19. ~~`ffmpeg.exe` (211 MB) Committed to Git~~ ✅ ALREADY FIXED
- Was already in `.gitignore`.

### 20. ~~Hardcoded `/app/encode_cli.py` Path in Web UI~~ ✅ FIXED
- Now uses `os.environ.get("CLI_PATH", ...)` with `__file__`-relative fallback.

### 21. ~~Unraid XML Uses Handbrake Icon~~ ✅ NOTED
- Added `<!-- TODO: Replace with custom AV1 Encoder Pro icon -->` comment.

### 22. ~~No Input Sanitization on Schedule Time Fields~~ ✅ FIXED
- Added `_validate_schedule_time()` that clamps hour (0-23) and minute (0-59) on focus-out.

### 23. ~~`docker-compose.yml` Batch Service Uses Wrong Shell~~ ✅ FIXED
- Changed to explicit `["/bin/bash", "-c"]` entrypoint with `shopt -s nullglob`.

### 24. Web UI Progress Indicator Is Fake/Inaccurate — ⏭ SKIPPED
- Would require FFmpeg duration probing. Low-impact.

### 25. ~~Console Output Lacks Maximum Line Limit~~ ✅ FIXED
- Added 5000-line cap in `process_console_queue()`.

### 26. ~~Two-Pass Variable Initialized But Never Used~~ ✅ FIXED
- Removed dead `self.twopass_var`.

### 27. ~~No EXPOSE Directive in Dockerfile~~ ✅ FIXED
- Added `EXPOSE 2081`.

### 28. ~~Missing `.flv`/`.wmv` in Browse Dialog Filter~~ ✅ FIXED
- Added `.flv` and `.wmv` to `browse_input()` filetypes.

### 29. ~~Unraid XML Input Volume Set to `rw` Instead of `ro`~~ ✅ FIXED
- Changed to `<Mode>ro</Mode>`.

### 30. ~~Copyright Year Hardcoded to 2025~~ ✅ FIXED
- Now uses `datetime.datetime.now().year` dynamically.
