# AV1 Video Encoder Pro
# Professional AV1 video encoding application

import customtkinter as ctk
import tkinter as tk
from PIL import Image
import os
import sys
import subprocess
import threading
import queue
import datetime
import windnd
import webbrowser

# Set appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# EXACT colors from Mastergui.png
COLORS = {
    'bg': '#0d1117',           # Main dark background
    'card': '#161b22',          # Card background (slightly lighter)
    'input': '#21262d',         # Input field background
    'accent': '#7c4dff',        # Purple accent
    'cyan': '#22d3ee',          # Cyan for console
    'text': '#e6edf3',          # Main text color
    'text_dim': '#8b949e',      # Dimmed text
    'console_bg': '#010409',    # Very dark console background
    'border': '#525964',        # Border color for cards (Lighter)
}


class AV1EncoderPro(ctk.CTk):
    @staticmethod
    def resource_path(relative_path):
        """Get path to resource for PyInstaller bundled exe"""
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)
    
    def __init__(self):
        super().__init__()
        
        self.title("AV1 Video Encoder Pro")
        self.geometry("820x780")
        self.configure(fg_color=COLORS['bg'])
        self.resizable(False, False)
        
        # Set window icon
        try:
            icon_path = self.resource_path("assets/CustomTkinter_icon_Windows.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except (OSError, tk.TclError):
            pass  # Icon not critical
        
        # Console queue
        self.console_queue = queue.Queue()
        self.after(100, self.process_console_queue)
        
        # Build UI
        self.build_tabs()
        
        # Tab content container
        self.tab_container = ctk.CTkFrame(self, fg_color="transparent")
        self.tab_container.pack(fill="both", expand=True, padx=25)
        
        # Create all tab content frames
        self.tab_frames = {}
        self.current_tab = "Video Encoder"
        
        # Video Encoder tab (main content)
        self.build_video_encoder_tab()
        
        # Other tabs
        self.build_batch_tab()
        self.build_scheduler_tab()
        self.build_settings_tab()
        self.build_about_tab()
        
        # Show Video Encoder by default
        self.show_tab("Video Encoder")
        
        # Console at bottom
        self.build_console()
        
        # Check FFmpeg
        self.check_ffmpeg()
        
        # Track active encoding processes for cleanup
        self.active_processes = []
        
        # Setup Drag and Drop
        windnd.hook_dropfiles(self, func=self.on_drop)
        
        # Handle window close - kill running processes
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def on_closing(self):
        """Clean up running processes when window is closed"""
        for proc in self.active_processes:
            try:
                if proc.poll() is None:  # Process still running
                    proc.terminate()
                    proc.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    proc.kill()  # Force kill if terminate fails
                except OSError:
                    pass
        self.destroy()
    
    def on_drop(self, filenames):
        """Handle dropped files/folders"""
        if not filenames:
            return
            
        # windnd returns bytes on Python 3, need to decode
        paths = []
        for f in filenames:
            if isinstance(f, bytes):
                f = f.decode("utf-8")
            paths.append(f)
        
        # Check if we're on Batch Processing tab
        if self.current_tab == "Batch Processing":
            video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm', '.wmv', '.flv')
            added_count = 0
            
            for path in paths:
                if os.path.isdir(path):
                    # It's a folder - add all video files inside
                    self.log(f"[INFO] Folder dropped: {path}")
                    for f in os.listdir(path):
                        if f.lower().endswith(video_extensions):
                            full_path = os.path.join(path, f)
                            if full_path not in self.batch_files:
                                self.batch_files.append(full_path)
                                self.batch_listbox.insert("end", full_path + "\n")
                                added_count += 1
                elif os.path.isfile(path) and path.lower().endswith(video_extensions):
                    # It's a video file
                    if path not in self.batch_files:
                        self.batch_files.append(path)
                        self.batch_listbox.insert("end", path + "\n")
                        added_count += 1
            
            if added_count > 0:
                self.log(f"[INFO] Added {added_count} files to batch queue.")
            else:
                self.log("[INFO] No video files found in dropped items.")
            return
        
        # Default: Video Encoder tab - single file behavior
        file_path = paths[0]
        self.log(f"[INFO] File dropped: {file_path}")
        self.input_var.set(file_path)
        
        # Auto-set output path
        folder = os.path.dirname(file_path)
        name = os.path.splitext(os.path.basename(file_path))[0]
        ext = ".webm" if self.format_var.get() == "WebM" else ".mp4"
        self.output_var.set(os.path.join(folder, f"{name}_AV1{ext}"))
        self.update_summary()
    
    # build_header removed to match "make it look like" screenshot (merged into tabs)
    
    def build_tabs(self):
        """Tab bar with integrated AV1 Logo"""
        tab_frame = ctk.CTkFrame(self, fg_color="transparent")
        tab_frame.pack(fill="x", padx=25, pady=(20, 10))
        
        # Left: Tabs container
        tabs_container = ctk.CTkFrame(tab_frame, fg_color="transparent")
        tabs_container.pack(side="left", fill="y")
        
        tabs = ["Video Encoder", "Batch Processing", "Scheduler", "Settings", "About"]
        self.tab_btns = {}
        
        for i, tab in enumerate(tabs):
            is_active = (i == 0)
            btn = ctk.CTkButton(
                tabs_container, text=tab,
                fg_color=COLORS['accent'] if is_active else "transparent",
                hover_color="#6b3fd4" if is_active else "#21262d",
                text_color="white" if is_active else COLORS['text_dim'],
                font=ctk.CTkFont(size=12, weight="bold" if is_active else "normal"),
                corner_radius=4, height=32,
                border_width=0,
                command=lambda t=tab: self.switch_tab(t)
            )
            btn.pack(side="left", padx=(0, 4))
            self.tab_btns[tab] = btn
            

    
    def switch_tab(self, name):
        """Switch tab button styling and content"""
        for t, btn in self.tab_btns.items():
            if t == name:
                btn.configure(fg_color=COLORS['accent'], text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=COLORS['text_dim'])
        self.show_tab(name)
    
    def show_tab(self, name):
        """Show/hide tab content frames"""
        for tab_name, frame in self.tab_frames.items():
            if tab_name == name:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()
        self.current_tab = name
    
    def build_video_encoder_tab(self):
        """Video Encoder tab - main encoding interface"""
        frame = ctk.CTkFrame(self.tab_container, fg_color="transparent")
        self.tab_frames["Video Encoder"] = frame
        
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        
        # Row 0: Input Source + Output Destination
        self.build_input_card(frame)
        self.build_output_card(frame)
        
        # Row 1: Encoding Options (Left)
        self.build_encoding_card(frame)
        
        # Row 1 (Right): Container for Summary + Audio to stack them tightly
        right_panel = ctk.CTkFrame(frame, fg_color="transparent")
        right_panel.grid(row=1, column=1, sticky="new", padx=(6, 0), pady=(6, 0))
        
        self.build_summary_card(right_panel)
        # Audio Options BELOW Summary
        self.build_audio_card(right_panel)
        # Buttons BELOW Audio Options
        self.build_buttons(right_panel)
    
    def build_batch_tab(self):
        """Batch Processing tab"""
        frame = ctk.CTkFrame(self.tab_container, fg_color="transparent")
        self.tab_frames["Batch Processing"] = frame
        
        card = ctk.CTkFrame(frame, fg_color=COLORS['card'], corner_radius=0)
        card.pack(fill="both", expand=True, pady=(0, 10))
        
        ctk.CTkLabel(card, text="Batch Processing",
                    font=ctk.CTkFont(size=18, weight="bold"),
                    text_color="white").pack(anchor="w", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(card, text="Add multiple video files to encode in batch.",
                    font=ctk.CTkFont(size=12),
                    text_color=COLORS['text_dim']).pack(anchor="w", padx=15, pady=(0, 15))
        
        self.batch_files = []
        self.batch_listbox = ctk.CTkTextbox(card, height=150,
                                            fg_color=COLORS['input'],
                                            text_color="white")
        self.batch_listbox.pack(fill="x", padx=15, pady=(0, 10))
        
        # Save to Folder option
        save_row = ctk.CTkFrame(card, fg_color="transparent")
        save_row.pack(fill="x", padx=15, pady=(0, 10))
        
        ctk.CTkLabel(save_row, text="Save to Folder:",
                    font=ctk.CTkFont(size=11),
                    text_color=COLORS['text']).pack(side="left")
        
        self.batch_output_var = ctk.StringVar()
        self.batch_output_entry = ctk.CTkEntry(save_row, textvariable=self.batch_output_var,
                                               fg_color=COLORS['input'], border_width=1,
                                               border_color=COLORS['text_dim'],
                                               text_color="white", height=30,
                                               placeholder_text="Same as source (default)")
        self.batch_output_entry.pack(side="left", fill="x", expand=True, padx=(10, 8))
        
        ctk.CTkButton(save_row, text="Browse",
                     fg_color=COLORS['input'], hover_color="#2d333b",
                     text_color="white", width=70, height=30,
                     corner_radius=4, command=self.batch_browse_output).pack(side="right")
        
        # Schedule toggle row
        schedule_row = ctk.CTkFrame(card, fg_color="transparent")
        schedule_row.pack(fill="x", padx=15, pady=(0, 10))
        
        self.schedule_enabled_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(schedule_row, text="Schedule Encoding",
                     variable=self.schedule_enabled_var,
                     font=ctk.CTkFont(size=11),
                     text_color=COLORS['text'],
                     fg_color=COLORS['text_dim'],
                     progress_color=COLORS['accent'],
                     button_color="white",
                     command=self.toggle_schedule).pack(side="left")
        
        self.schedule_time_label = ctk.CTkLabel(schedule_row, text="",
                                                font=ctk.CTkFont(size=11),
                                                text_color=COLORS['accent'])
        self.schedule_time_label.pack(side="left", padx=(15, 0))
        
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkButton(btn_row, text="Add Folder",
                     fg_color=COLORS['accent'], hover_color="#6b3fd4",
                     width=100, height=32,
                     command=self.batch_add_folder).pack(side="left", padx=(0, 8))
        
        ctk.CTkButton(btn_row, text="Clear",
                     fg_color=COLORS['input'], hover_color="#2d333b",
                     width=80, height=32,
                     command=self.batch_clear).pack(side="left", padx=(0, 8))
        
        self.batch_start_btn = ctk.CTkButton(btn_row, text="Start Batch",
                     fg_color=COLORS['accent'], hover_color="#6b3fd4",
                     width=100, height=32,
                     command=self.batch_start)
        self.batch_start_btn.pack(side="right")
    
    def toggle_schedule(self):
        """Toggle schedule mode and update display"""
        if self.schedule_enabled_var.get():
            # Get time from scheduler tab
            hour = self.schedule_hour.get() or "00"
            minute = self.schedule_min.get() or "00"
            day = self.schedule_date_var.get()
            self.schedule_time_label.configure(text=f"{day} at {hour}:{minute}")
            self.batch_start_btn.configure(text="Schedule")
        else:
            self.schedule_time_label.configure(text="")
            self.batch_start_btn.configure(text="Start Batch")
    
    def batch_browse_output(self):
        """Browse for batch output folder"""
        from tkinter import filedialog
        folder = filedialog.askdirectory()
        if folder:
            self.batch_output_var.set(folder)
    
    def build_scheduler_tab(self):
        """Scheduler tab - Set time for scheduled batch encoding"""
        frame = ctk.CTkFrame(self.tab_container, fg_color="transparent")
        self.tab_frames["Scheduler"] = frame
        
        # Time settings card
        card = ctk.CTkFrame(frame, fg_color=COLORS['card'], corner_radius=6,
                           border_width=1, border_color=COLORS['border'])
        card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(card, text="Schedule Settings",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="white").pack(anchor="w", padx=12, pady=(12, 4))
        
        ctk.CTkLabel(card, text="Set the time for scheduled batch encoding",
                    font=ctk.CTkFont(size=10),
                    text_color=COLORS['text_dim']).pack(anchor="w", padx=12, pady=(0, 15))
        
        # Date/Time Selection
        time_row = ctk.CTkFrame(card, fg_color="transparent")
        time_row.pack(fill="x", padx=12, pady=(0, 15))
        
        ctk.CTkLabel(time_row, text="When:",
                    font=ctk.CTkFont(size=11),
                    text_color=COLORS['text'], width=60).pack(side="left")
        
        self.schedule_date_var = ctk.StringVar(value="Today")
        ctk.CTkOptionMenu(time_row, variable=self.schedule_date_var,
                         values=["Today", "Tomorrow"],
                         fg_color=COLORS['input'], button_color=COLORS['input'],
                         button_hover_color="#2d333b", dropdown_fg_color=COLORS['card'],
                         width=100, height=30).pack(side="left", padx=(0, 15))
        
        ctk.CTkLabel(time_row, text="at",
                    font=ctk.CTkFont(size=11),
                    text_color=COLORS['text']).pack(side="left", padx=(0, 8))
        
        self.schedule_hour = ctk.CTkEntry(time_row, width=50, height=30,
                                         fg_color=COLORS['input'], 
                                         text_color="white",
                                         placeholder_text="HH",
                                         justify="center")
        self.schedule_hour.pack(side="left")
        
        ctk.CTkLabel(time_row, text=":",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=COLORS['text']).pack(side="left", padx=4)
        
        self.schedule_min = ctk.CTkEntry(time_row, width=50, height=30,
                                        fg_color=COLORS['input'],
                                        text_color="white",
                                        placeholder_text="MM",
                                        justify="center")
        self.schedule_min.pack(side="left")
        
        # Info text
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(fill="x", padx=12, pady=(0, 12))
        
        ctk.CTkLabel(info_frame, 
                    text="Enable 'Schedule Encoding' in Batch Processing tab to use this time",
                    font=ctk.CTkFont(size=10),
                    text_color=COLORS['text_dim']).pack(anchor="w")

    def build_settings_tab(self):
        """Settings tab with encoder options and threading"""
        frame = ctk.CTkFrame(self.tab_container, fg_color="transparent")
        self.tab_frames["Settings"] = frame
        
        # Scrollable container for settings
        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True, pady=(0, 10))
        
        # === ENCODER SELECTION ===
        enc_card = ctk.CTkFrame(scroll, fg_color=COLORS['card'], corner_radius=6,
                               border_width=1, border_color=COLORS['border'])
        enc_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(enc_card, text="AV1 Encoder",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="white").pack(anchor="w", padx=12, pady=(12, 4))
        
        ctk.CTkLabel(enc_card, text="Select the encoder to use for AV1 video encoding",
                    font=ctk.CTkFont(size=10),
                    text_color=COLORS['text_dim']).pack(anchor="w", padx=12, pady=(0, 8))
        
        # Encoder options with descriptions
        encoders = [
            ("SVT-AV1 (CPU)", "libsvtav1", "Best quality/speed balance. Uses all CPU cores. Recommended."),
            ("libaom (CPU)", "libaom-av1", "Reference encoder. Highest quality but very slow."),
            ("rav1e (CPU)", "librav1e", "Rust-based encoder. Good quality, slower than SVT-AV1."),
            ("NVENC (NVIDIA GPU)", "av1_nvenc", "Hardware encoding. Very fast. Requires RTX 40 series."),
            ("AMF (AMD GPU)", "av1_amf", "Hardware encoding. Very fast. Requires RX 7000 series."),
            ("QSV (Intel GPU)", "av1_qsv", "Hardware encoding. Fast. Requires Intel Arc GPU."),
            ("Vulkan (GPU)", "av1_vulkan", "Cross-platform GPU encoding via Vulkan API."),
        ]
        
        self.encoder_var = ctk.StringVar(value="libsvtav1")
        
        for name, value, tooltip in encoders:
            row = ctk.CTkFrame(enc_card, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=2)
            
            rb = ctk.CTkRadioButton(row, text=name, variable=self.encoder_var,
                                   value=value, font=ctk.CTkFont(size=11),
                                   text_color=COLORS['text'],
                                   fg_color=COLORS['accent'],
                                   hover_color="#6b3fd4",
                                   border_color=COLORS['text_dim'])
            rb.pack(side="left")
            
            # Tooltip/description
            ctk.CTkLabel(row, text=f"  ({tooltip})",
                        font=ctk.CTkFont(size=9),
                        text_color=COLORS['text_dim']).pack(side="left")
        
        # Spacing
        ctk.CTkFrame(enc_card, height=8, fg_color="transparent").pack()
        
        # === THREADING OPTIONS ===
        thread_card = ctk.CTkFrame(scroll, fg_color=COLORS['card'], corner_radius=6,
                                  border_width=1, border_color=COLORS['border'])
        thread_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(thread_card, text="CPU Threading",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="white").pack(anchor="w", padx=12, pady=(12, 4))
        
        ctk.CTkLabel(thread_card, text="Control how many CPU threads to use (CPU encoders only)",
                    font=ctk.CTkFont(size=10),
                    text_color=COLORS['text_dim']).pack(anchor="w", padx=12, pady=(0, 8))
        
        thread_row = ctk.CTkFrame(thread_card, fg_color="transparent")
        thread_row.pack(fill="x", padx=12, pady=(0, 12))
        
        ctk.CTkLabel(thread_row, text="Threads:",
                    font=ctk.CTkFont(size=11),
                    text_color=COLORS['text']).pack(side="left")
        
        max_threads = os.cpu_count() or 8
        self.thread_var = ctk.IntVar(value=0)  # 0 = Auto
        
        self.thread_label = ctk.CTkLabel(thread_row, text="Auto",
                                        font=ctk.CTkFont(size=11, weight="bold"),
                                        text_color=COLORS['accent'])
        self.thread_label.pack(side="right")
        
        def update_thread_label(val):
            v = int(float(val))
            self.thread_var.set(v)
            self.thread_label.configure(text="Auto" if v == 0 else str(v))
        
        thread_slider = ctk.CTkSlider(thread_row, from_=0, to=max_threads,
                                     number_of_steps=max_threads,
                                     fg_color=COLORS['input'],
                                     progress_color=COLORS['accent'],
                                     button_color=COLORS['accent'],
                                     button_hover_color="#6b3fd4",
                                     command=update_thread_label)
        thread_slider.set(0)
        thread_slider.pack(side="right", padx=(10, 10), fill="x", expand=True)
        
        # Info note
        ctk.CTkLabel(thread_card, text="💡 Auto uses all available cores. Lower values reduce CPU usage.",
                    font=ctk.CTkFont(size=9),
                    text_color=COLORS['text_dim']).pack(anchor="w", padx=12, pady=(0, 12))
        
        # === GPU INFO ===
        gpu_card = ctk.CTkFrame(scroll, fg_color=COLORS['card'], corner_radius=6,
                               border_width=1, border_color=COLORS['border'])
        gpu_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(gpu_card, text="GPU Hardware Requirements",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="white").pack(anchor="w", padx=12, pady=(12, 8))
        
        gpu_info = [
            "• NVENC: NVIDIA GeForce RTX 4000 series or newer",
            "• AMF: AMD Radeon RX 7000 series or newer", 
            "• QSV: Intel Arc A-series GPUs",
            "• Vulkan: Any GPU with Vulkan 1.3+ support",
            "",
            "⚠️ If your GPU doesn't support AV1 encoding, the encoder will fail.",
            "   In that case, use SVT-AV1 (CPU) which works on all systems."
        ]
        
        for line in gpu_info:
            ctk.CTkLabel(gpu_card, text=line,
                        font=ctk.CTkFont(size=10),
                        text_color=COLORS['text_dim'] if line.startswith("•") or line.startswith("⚠") or line.startswith(" ") else COLORS['text'],
                        justify="left").pack(anchor="w", padx=12, pady=1)
        
        ctk.CTkFrame(gpu_card, height=8, fg_color="transparent").pack()
    
    def build_about_tab(self):
        """About tab"""
        frame = ctk.CTkFrame(self.tab_container, fg_color="transparent")
        self.tab_frames["About"] = frame
        
        # Background color transparent to blend with window
        card = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
        card.pack(fill="both", expand=True, pady=(0, 10))
        
        # Logo at original dimensions
        try:
            # Use cleaned transparent logo if available
            # Prioritize assets folder path
            logo_name = "assets/av1_codec_logo.png"
            if not os.path.exists(self.resource_path(logo_name)):
                logo_name = "av1_codec_logo.png"
                
            logo_path = self.resource_path(logo_name)
            if os.path.exists(logo_path):
                logo_img = Image.open(logo_path)
                # Use original size, no resize
                w, h = logo_img.size
                
                # Check for scale factor to fit window if huge
                max_w = 600
                if w > max_w:
                    ratio = max_w / w
                    w = int(w * ratio)
                    h = int(h * ratio)
                    
                logo = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(w, h))
                ctk.CTkLabel(card, image=logo, text="").pack(pady=(40, 20))
        except Exception:
            # Logo loading failed - non-critical, continue without logo
            pass
            
        ctk.CTkLabel(card, text="Version 1.1.0",
                    font=ctk.CTkFont(size=12)).pack(pady=(0, 10))
                    
        ctk.CTkLabel(card, text="A modern AV1 video encoder powered by FFmpeg and SVT-AV1.",
                    font=ctk.CTkFont(size=11), text_color=COLORS['text'],
                    justify="center").pack(pady=(0, 20))
        
        # GitHub Button
        github_btn = ctk.CTkButton(card, text="GitHub Repository",
                                  fg_color="transparent", border_width=1,
                                  border_color=COLORS['text_dim'],
                                  text_color=COLORS['text'],
                                  hover_color="#30363d",
                                  width=140, height=32,
                                  command=lambda: webbrowser.open("https://github.com/3453-315h"))
        github_btn.pack(pady=(0, 20))
        
        ctk.CTkLabel(card, text="© 2025 AV1 Encoder Pro",
                    font=ctk.CTkFont(size=10),
                    text_color=COLORS['text_dim']).pack(pady=(10, 20))
    
    def batch_add_folder(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory()
        if not folder:
            return
            
        video_exts = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}
        count = 0
        for root, dirs, files in os.walk(folder):
            for file in files:
                if os.path.splitext(file.lower())[1] in video_exts:
                    full_path = os.path.join(root, file)
                    if full_path not in self.batch_files:
                        self.batch_files.append(full_path)
                        self.batch_listbox.insert("end", full_path + "\n")
                        count += 1
                        
        self.log(f"[INFO] Added {count} files from folder.")
    
    def batch_clear(self):
        self.batch_files = []
        self.batch_listbox.delete("1.0", "end")
    
    def batch_start(self):
        if not self.batch_files:
            self.log("[ERROR] No files in batch queue.")
            return
        
        # Check if scheduled encoding is enabled
        if hasattr(self, 'schedule_enabled_var') and self.schedule_enabled_var.get():
            # Calculate delay until scheduled time
            try:
                hour = int(self.schedule_hour.get() or 0)
                minute = int(self.schedule_min.get() or 0)
                
                now = datetime.datetime.now()
                scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                if self.schedule_date_var.get() == "Tomorrow":
                    scheduled += datetime.timedelta(days=1)
                elif scheduled <= now:
                    # If time already passed today, schedule for tomorrow
                    scheduled += datetime.timedelta(days=1)
                
                delay = (scheduled - now).total_seconds()
                
                if delay > 0:
                    self.log(f"[SCHEDULED] Batch will start at {scheduled.strftime('%Y-%m-%d %H:%M')}")
                    self.log(f"[INFO] Waiting {int(delay // 60)} minutes...")
                    threading.Thread(target=self._scheduled_batch_start, args=(delay,), daemon=True).start()
                    return
            except (ValueError, AttributeError):
                self.log("[WARNING] Invalid schedule time, starting immediately...")
        
        self.log(f"[INFO] Starting batch of {len(self.batch_files)} files...")
        threading.Thread(target=self.run_batch, daemon=True).start()
    
    def _scheduled_batch_start(self, delay):
        """Wait for scheduled time then start batch"""
        import time
        time.sleep(delay)
        self.log(f"[INFO] Schedule triggered! Starting batch of {len(self.batch_files)} files...")
        self.run_batch()
    
    def run_batch(self):
        """Run batch encoding of all files"""
        try:
            q = self.quality_var.get()
            crf = int(63 - (q * 0.63))
            preset = self.preset_var.get().split()[0]
        except (AttributeError, ValueError, IndexError):
            crf = 30
            preset = "6"
            
        for i, inp in enumerate(self.batch_files):
            self.log(f"[BATCH {i+1}/{len(self.batch_files)}] {os.path.basename(inp)}")
            
            # Use custom output folder if specified, else same as source
            custom_folder = getattr(self, 'batch_output_var', ctk.StringVar()).get()
            folder = custom_folder if custom_folder else os.path.dirname(inp)
            
            name = os.path.splitext(os.path.basename(inp))[0]
            # Output extension based on dropdown
            ext = ".webm" if self.format_var.get() == "WebM" else ".mp4"
            out = os.path.join(folder, f"{name}_AV1{ext}")
            
            try:
                steps = self.compile_encode_commands(inp, out, crf, preset)
                for step_name, cmd in steps:
                    self.log(f"  > Executing {step_name}...")
                    try:
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        startupinfo.wShowWindow = subprocess.SW_HIDE
                        
                        # Set UTF-8 environment for unicode filename support
                        env = os.environ.copy()
                        env['PYTHONIOENCODING'] = 'utf-8'
                        env['PYTHONUTF8'] = '1'
                        
                        result = subprocess.run(
                            cmd, 
                            capture_output=True, 
                            check=True,
                            startupinfo=startupinfo,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            env=env
                        )
                    except subprocess.CalledProcessError as cpe:
                        stderr = cpe.stderr.decode('utf-8', errors='replace') if isinstance(cpe.stderr, bytes) else cpe.stderr
                        self.log(f"[ERROR] FFmpeg Error:\n{stderr}")
                        raise cpe
                        
                self.log(f"[DONE] {os.path.basename(out)}")
            except Exception as e:
                if not isinstance(e, subprocess.CalledProcessError):
                     self.log(f"[ERROR] Failed {os.path.basename(inp)}: {str(e)}")
        
        self.log("[BATCH COMPLETED]")
    
    def build_input_card(self, parent):
        """Input Source card"""
        card = ctk.CTkFrame(parent, fg_color=COLORS['card'], corner_radius=6, 
                          border_width=1, border_color=COLORS['border'])
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 6))
        
        ctk.CTkLabel(card, text="Input Source",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="white").pack(anchor="w", padx=12, pady=(12, 2))
        
        ctk.CTkLabel(card, text="File Selection",
                    font=ctk.CTkFont(size=10),
                    text_color=COLORS['text_dim']).pack(anchor="w", padx=12, pady=(0, 8))
        
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 12))
        
        self.browse_in_btn = ctk.CTkButton(row, text="Browse",
                                           fg_color=COLORS['input'], hover_color="#2d333b",
                                           text_color="white", width=70, height=30,
                                           corner_radius=4, command=self.browse_input)
        self.browse_in_btn.pack(side="left")
        
        self.input_var = ctk.StringVar()
        self.input_entry = ctk.CTkEntry(row, textvariable=self.input_var,
                                        fg_color=COLORS['card'], border_width=1,
                                        border_color=COLORS['text_dim'],
                                        text_color="white", height=30,
                                        placeholder_text="Drop file here or click Browse")
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(8, 0))
    
    def build_output_card(self, parent):
        """Output Destination card"""
        card = ctk.CTkFrame(parent, fg_color=COLORS['card'], corner_radius=6, 
                          border_width=1, border_color=COLORS['border'])
        card.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 6))
        
        ctk.CTkLabel(card, text="Output Destination",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="white").pack(anchor="w", padx=12, pady=(12, 2))
        
        ctk.CTkLabel(card, text="Save As",
                    font=ctk.CTkFont(size=10),
                    text_color=COLORS['text_dim']).pack(anchor="w", padx=12, pady=(0, 8))
        
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 12))
        
        self.output_var = ctk.StringVar()
        self.output_entry = ctk.CTkEntry(row, textvariable=self.output_var,
                                         fg_color=COLORS['card'], border_width=1,
                                         border_color=COLORS['text_dim'],
                                         text_color="white", height=30)
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        self.browse_out_btn = ctk.CTkButton(row, text="Browse",
                                            fg_color=COLORS['input'], hover_color="#2d333b",
                                            text_color="white", width=70, height=30,
                                            corner_radius=4, command=self.browse_output)
        self.browse_out_btn.pack(side="right")
    
    def build_encoding_card(self, parent):
        """Encoding Options card"""
        card = ctk.CTkFrame(parent, fg_color=COLORS['card'], corner_radius=6, 
                          border_width=1, border_color=COLORS['border'])
        card.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(6, 0))
        
        ctk.CTkLabel(card, text="Encoding Options",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="white").pack(anchor="w", padx=12, pady=(12, 10))
        
        # Quality row
        q_row = ctk.CTkFrame(card, fg_color="transparent")
        q_row.pack(fill="x", padx=12)
        
        ctk.CTkLabel(q_row, text="Quality (%)",
                    font=ctk.CTkFont(size=11),
                    text_color=COLORS['text']).pack(side="left")
        
        self.quality_var = ctk.IntVar(value=50)
        self.crf_label = ctk.StringVar(value="50% (CRF 30)")
        
        ctk.CTkLabel(q_row, textvariable=self.crf_label,
                    font=ctk.CTkFont(size=10),
                    text_color=COLORS['text']).pack(side="right")
        
        # Slider
        self.slider = ctk.CTkSlider(card, from_=0, to=100, variable=self.quality_var,
                                   progress_color=COLORS['accent'],
                                   button_color="white", button_hover_color="#e0e0e0",
                                   command=self.update_quality)
        self.slider.pack(fill="x", padx=12, pady=(4, 12))
        
        # Dropdowns - minimal flat style
        self.preset_var = ctk.StringVar(value="6 (Balanced)")
        self.make_dropdown(card, "Speed Preset", self.preset_var,
                          ["0 (Slowest)", "2", "4", "6 (Balanced)", "8", "10", "12 (Fastest)"])
        
        self.format_var = ctk.StringVar(value="WebM")
        self.make_dropdown(card, "Output Format", self.format_var, ["WebM", "MP4"],
                          command=self.update_output_extension)
        
        # Audio moved to separate card
        
        # Advanced AV1 Settings
        
        # Advanced AV1 Settings
        self.tune_var = ctk.StringVar(value="VQ (Visual Quality)")
        self.make_dropdown(card, "Tune", self.tune_var,
                          ["VQ (Visual Quality)", "PSNR", "SSIM", "Film"])
        
        self.resolution_var = ctk.StringVar(value="Original")
        self.make_dropdown(card, "Resolution", self.resolution_var,
                          ["Original", "4K (3840x2160)", "1080p (1920x1080)", "720p (1280x720)", "480p (854x480)"])
        
        # Film Grain row
        grain_row = ctk.CTkFrame(card, fg_color="transparent")
        grain_row.pack(fill="x", padx=12, pady=4)
        
        ctk.CTkLabel(grain_row, text="Film Grain",
                    font=ctk.CTkFont(size=11),
                    text_color=COLORS['text']).pack(side="left")
        
        self.grain_var = ctk.IntVar(value=0)
        self.grain_label = ctk.StringVar(value="0")
        
        ctk.CTkLabel(grain_row, textvariable=self.grain_label,
                    font=ctk.CTkFont(size=10),
                    text_color=COLORS['text'], width=30).pack(side="right")
        
        self.grain_slider = ctk.CTkSlider(grain_row, from_=0, to=50, variable=self.grain_var,
                                         width=100, progress_color=COLORS['accent'],
                                         button_color="white", button_hover_color="#e0e0e0",
                                         command=lambda v: self.grain_label.set(str(int(v))))
        self.grain_slider.pack(side="right", padx=(0, 10))
        
        # twopass_var kept for compatibility
        self.twopass_var = ctk.BooleanVar(value=False)
    
    def make_dropdown(self, parent, label, var, values, command=None):
        """Minimal flat dropdown matching Mastergui.png"""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=2)
        
        ctk.CTkLabel(row, text=label,
                    font=ctk.CTkFont(size=11),
                    text_color=COLORS['text']).pack(side="left")
        
        dd = ctk.CTkOptionMenu(row, variable=var, values=values,
                              fg_color=COLORS['input'],
                              button_color=COLORS['input'],
                              button_hover_color="#2d333b",
                              dropdown_fg_color=COLORS['input'],
                              dropdown_hover_color=COLORS['accent'],
                              text_color="white",
                              width=180, height=28, corner_radius=4,
                              command=command)
        dd.pack(side="right")
    
    def build_summary_card(self, parent):
        """Summary card"""
        # Summary card
        card = ctk.CTkFrame(parent, fg_color=COLORS['card'], corner_radius=6,
                          border_width=1, border_color=COLORS['border'])
        card.pack(fill="x", pady=(0, 6))
        
        ctk.CTkLabel(card, text="Summary",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="white").pack(anchor="w", padx=12, pady=(10, 4))
        
        self.summary_var = ctk.StringVar(value="Select an input file to see summary.")
        ctk.CTkLabel(card, textvariable=self.summary_var,
                    font=ctk.CTkFont(size=11),
                    text_color=COLORS['text'],
                    justify="left", anchor="nw",
                    wraplength=300).pack(anchor="nw", padx=12, pady=(0, 12))
    
    def build_buttons(self, parent):
        """Build action buttons separately"""
        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", pady=(6, 0))
        
        # Spacer to push buttons right
        ctk.CTkFrame(btn_row, fg_color="transparent", width=1).pack(side="left", expand=True)
        
        self.encode_btn = ctk.CTkButton(btn_row, text="Encode Video",
                                        fg_color=COLORS['accent'],
                                        hover_color="#6b3fd4",
                                        text_color="white",
                                        font=ctk.CTkFont(size=12, weight="bold"),
                                        width=140, height=36, corner_radius=6,
                                        command=self.start_encode)
        self.encode_btn.pack(side="left", padx=(0, 8))
        
        self.reset_btn = ctk.CTkButton(btn_row, text="Reset",
                                       fg_color=COLORS['input'],
                                       hover_color="#2d333b",
                                       text_color="white",
                                       font=ctk.CTkFont(size=12),
                                       width=70, height=36, corner_radius=6,
                                       command=self.reset_form)
        self.reset_btn.pack(side="left")
    
    def build_console(self):
        """Output Console with cyan border"""
        console_frame = ctk.CTkFrame(self, fg_color="transparent")
        console_frame.pack(fill="x", padx=25, pady=(15, 20))
        
        ctk.CTkLabel(console_frame, text="Output Console",
                    font=ctk.CTkFont(size=11),
                    text_color=COLORS['text_dim']).pack(anchor="w", pady=(0, 6))
        
        self.console = ctk.CTkTextbox(console_frame, height=140,
                                      fg_color=COLORS['console_bg'],
                                      text_color=COLORS['cyan'],
                                      border_width=1,
                                      border_color=COLORS['cyan'],
                                      font=ctk.CTkFont(family="Consolas", size=11))
        self.console.pack(fill="x")
    
    # ============ FUNCTIONALITY ============
    
    def browse_input(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov *.webm"), ("All", "*.*")]
        )
        if path:
            self.input_var.set(path)
            folder = os.path.dirname(path)
            name = os.path.splitext(os.path.basename(path))[0]
            ext = ".webm" if self.format_var.get() == "WebM" else ".mp4"
            self.output_var.set(os.path.join(folder, f"{name}_AV1{ext}"))
            self.update_summary()
    
    def build_audio_card(self, parent):
        """Audio Options card"""
        card = ctk.CTkFrame(parent, fg_color=COLORS['card'], corner_radius=6,
                          border_width=1, border_color=COLORS['border'])
        # Position using pack inside right panel
        card.pack(fill="x")
        
        ctk.CTkLabel(card, text="Audio Options",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="white").pack(anchor="w", padx=12, pady=(12, 10))

        # Audio Codec
        self.audio_var = ctk.StringVar(value="Opus (Recommended)")
        self.make_dropdown(card, "Audio Codec", self.audio_var,
                          ["Copy", "Opus (Recommended)", "AAC", "No Audio"])
                          
        # Audio Bitrate
        self.audio_bitrate_var = ctk.StringVar(value="128k")
        self.make_dropdown(card, "Bitrate", self.audio_bitrate_var,
                          ["64k", "96k", "128k", "192k", "256k", "320k"])
        
        # Bottom padding
        ctk.CTkFrame(card, height=12, fg_color="transparent").pack()
    
    def browse_output(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".webm" if self.format_var.get() == "WebM" else ".mp4",
            filetypes=[("WebM", "*.webm"), ("MP4", "*.mp4")]
        )
        if path:
            self.output_var.set(path)
            self.update_summary()
    
    
    def update_output_extension(self, choice):
        """Update output filename extension when format changes"""
        current_out = self.output_var.get()
        if not current_out:
            return
            
        base, ext = os.path.splitext(current_out)
        new_ext = ".mp4" if choice == "MP4" else ".webm"
        
        if ext.lower() != new_ext:
            self.output_var.set(base + new_ext)
            self.update_summary()

    def update_quality(self, val=None):
        q = self.quality_var.get()
        crf = int(63 - (q * 0.63))
        self.crf_label.set(f"{q}% (CRF {crf})")
        self.update_summary()
    
    def update_summary(self):
        inp = os.path.basename(self.input_var.get()) or "No file"
        # Determine actual video dimensions would require probing, hardcoding for visual match or keeping generic
        # Use generic or just parsed filename for now
        
        q = self.quality_var.get()
        crf = int(63 - (q * 0.63))
        preset = self.preset_var.get().split()[0]
        
        audio_full = self.audio_var.get()
        audio = "Copy Audio" if audio_full == "Copy" else audio_full
        
        self.summary_var.set(
            f"Input: {inp}\n"
            f"Output: {self.format_var.get()} (AV1, {audio}), CRF {crf}, Preset {preset}"
        )
    
    def log(self, msg):
        self.console_queue.put(msg + "\n")
    
    def process_console_queue(self):
        """Process queued console messages"""
        try:
            while True:
                msg = self.console_queue.get_nowait()
                self.console.insert("end", msg)
                self.console.see("end")
        except queue.Empty:
            pass
        self.after(100, self.process_console_queue)
    
    def check_ffmpeg(self):
        """Check for bundled or system FFmpeg"""
        self.ffmpeg_path = self.resource_path("ffmpeg.exe")
        if not os.path.exists(self.ffmpeg_path):
            # Fall back to system ffmpeg
            self.ffmpeg_path = "ffmpeg"
        
        try:
            result = subprocess.run([self.ffmpeg_path, "-version"], capture_output=True, text=True)
            if result.returncode == 0:
                self.log("[INFO] FFmpeg found - Video encoding enabled")
        except (FileNotFoundError, OSError):
            self.log("[ERROR] FFmpeg not found. Please install FFmpeg.")
    
    def start_encode(self):
        inp = self.input_var.get()
        out = self.output_var.get()
        if not inp:
            self.log("[ERROR] Please select an input file.")
            return
        
        q = self.quality_var.get()
        crf = int(63 - (q * 0.63))
        preset = self.preset_var.get().split()[0]
        
        self.log(f"[INFO] Input: {inp}")
        self.log(f"[INFO] Output: {out}")
        self.log(f"[INFO] Settings: CRF {crf}, Preset {preset}, Format {self.format_var.get()}, Audio {self.audio_var.get()}")
        self.log("Ready to encode.")
        
        threading.Thread(target=self.run_encode, args=(inp, out, crf, preset), daemon=True).start()
    
    def compile_encode_commands(self, inp, out, crf, preset):
        """Generate FFmpeg commands based on current UI settings"""
        # Audio
        audio = self.audio_var.get()
        bitrate = self.audio_bitrate_var.get()
        
        # Safety for WebM container: Force Opus if Copy is selected (usually AAC)
        is_webm = out.lower().endswith(".webm")
        
        if audio == "Copy":
            if is_webm:
                self.log("[INFO] 'Copy' audio into WebM is unsafe. Auto-switching to Opus (128k).")
                audio_opts = ["-c:a", "libopus", "-b:a", "128k"]
            else:
                audio_opts = ["-c:a", "copy"]
        elif audio == "Opus (Recommended)":
            audio_opts = ["-c:a", "libopus", "-b:a", bitrate]
        elif audio == "AAC":
            audio_opts = ["-c:a", "aac", "-b:a", bitrate]
        elif audio == "No Audio":
            audio_opts = ["-an"]
        else:
            audio_opts = ["-c:a", "copy"]

        # Tune
        tune = self.tune_var.get()
        tune_map = {"VQ (Visual Quality)": "0", "PSNR": "1", "SSIM": "2", "Film": "0"}
        tune_val = tune_map.get(tune, "0")

        # Resolution
        resolution = self.resolution_var.get()
        scale_opts = []
        if resolution != "Original":
            res_map = {
                "4K (3840x2160)": "3840:2160",
                "1080p (1920x1080)": "1920:1080",
                "720p (1280x720)": "1280:720",
                "480p (854x480)": "854:480"
            }
            if resolution in res_map:
                scale_opts = ["-vf", f"scale={res_map[resolution]}:flags=lanczos"]

        # Film Grain
        grain = self.grain_var.get()
        
        # Get encoder from Settings
        encoder = getattr(self, 'encoder_var', ctk.StringVar(value="libsvtav1")).get()
        threads = getattr(self, 'thread_var', ctk.IntVar(value=0)).get()
        
        # Log encoder
        self.log(f"[INFO] Encoder: {encoder}")
        
        # Check if encoder is SVT-AV1 (supports svtav1-params)
        is_svt = encoder == "libsvtav1"
        is_gpu = encoder in ["av1_nvenc", "av1_amf", "av1_qsv", "av1_vulkan"]
        
        # Build encoder-specific options
        encoder_opts = []
        
        if is_svt:
            svt_params = f"tune={tune_val}"
            if grain > 0:
                svt_params += f":film-grain={grain}:film-grain-denoise=1"
            if threads > 0:
                svt_params += f":logical_processors={threads}"
            encoder_opts = ["-c:v", encoder, "-crf", str(crf), "-preset", str(preset), "-svtav1-params", svt_params]
        elif is_gpu:
            # GPU encoders require specific hardware - warn user
            gpu_requirements = {
                "av1_nvenc": "NVIDIA RTX 40 series GPU",
                "av1_amf": "AMD RX 7000 series GPU", 
                "av1_qsv": "Intel Arc GPU",
                "av1_vulkan": "Vulkan-capable GPU with AV1 support"
            }
            self.log(f"[WARNING] {encoder} requires {gpu_requirements.get(encoder, 'specific GPU hardware')}")
            self.log("[INFO] If encoding fails, switch to SVT-AV1 (CPU) in Settings")
            
            # GPU encoders use different quality parameters
            encoder_opts = ["-c:v", encoder]
            if encoder == "av1_nvenc":
                encoder_opts.extend(["-cq", str(crf), "-preset", "p" + str(min(7, max(1, 8 - int(preset))))])
            elif encoder == "av1_amf":
                encoder_opts.extend(["-rc", "cqp", "-qp_i", str(crf), "-qp_p", str(crf)])
            elif encoder == "av1_qsv":
                encoder_opts.extend(["-global_quality", str(crf)])
            elif encoder == "av1_vulkan":
                encoder_opts.extend(["-qp", str(crf)])
        else:
            # libaom or rav1e (CPU encoders)
            encoder_opts = ["-c:v", encoder, "-crf", str(crf), "-cpu-used", str(preset)]
            if threads > 0:
                encoder_opts.extend(["-threads", str(threads)])

        # Build single-pass encode command
        cmd = [self.ffmpeg_path, "-y", "-i", inp]
        cmd.extend(encoder_opts)
        cmd.extend(scale_opts)
        cmd.extend(audio_opts)
        cmd.append(out)
        
        return [("ENCODE", cmd)]

    def run_encode(self, inp, out, crf, preset):
        try:
            steps = self.compile_encode_commands(inp, out, crf, preset)
            
            for name, cmd in steps:
                label = "[INFO]" if name == "ENCODE" else f"[{name}]"
                self.log(f"{label} Starting...")
                self.log(f"[CMD] {' '.join(cmd)}")
                
                # Use CREATE_NO_WINDOW and handle unicode properly
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
                # Set UTF-8 environment for unicode filename support
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                env['PYTHONUTF8'] = '1'
                
                process = subprocess.Popen(
                    cmd, 
                    stderr=subprocess.PIPE, 
                    stdout=subprocess.PIPE,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    env=env
                )
                self.active_processes.append(process)
                
                # Read stderr as bytes and decode
                for line in process.stderr:
                    try:
                        decoded = line.decode('utf-8', errors='replace') if isinstance(line, bytes) else line
                        if "frame=" in decoded or "size=" in decoded or "time=" in decoded:
                            self.log(f"{label} {decoded.strip()}")
                    except:
                        pass
                        
                process.wait()
                
                if process in self.active_processes:
                    self.active_processes.remove(process)
                
                if process.returncode != 0:
                    raise Exception(f"{name} failed with code {process.returncode}")
            
            self.log("[DONE] Encoding complete!")
            
        except Exception as e:
            self.log(f"[ERROR] {str(e)}")
    
    def reset_form(self):
        self.input_var.set("")
        self.output_var.set("")
        self.quality_var.set(50)
        self.crf_label.set("50% (CRF 30)")
        self.preset_var.set("6 (Balanced)")
        self.format_var.set("WebM")
        self.audio_var.set("Copy")
        self.tune_var.set("VQ (Visual Quality)")
        self.resolution_var.set("Original")
        self.grain_var.set(0)
        self.grain_label.set("0")
        self.summary_var.set("Select an input file to see summary.")


if __name__ == "__main__":
    try:
        app = AV1EncoderPro()
        app.mainloop()
    except Exception as e:
        import traceback
        print(f"[CRITICAL] Startup failed: {e}")
        traceback.print_exc()
        input("Press Enter to exit...")

