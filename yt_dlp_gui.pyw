import os
import sys
import json
import re
import threading
import winreg
import shutil
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import yt_dlp

# --- Ensure FFmpeg and Winget tools are in PATH ---
def setup_environment():
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return
    # Reload PATH from registry
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as k:
            user_path, _ = winreg.QueryValueEx(k, "Path")
            for p in user_path.split(";"):
                if p and os.path.exists(p) and p not in os.environ["PATH"]:
                    os.environ["PATH"] += os.pathsep + p
    except Exception:
        pass

    # Check Winget Links
    winget_links = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links")
    if os.path.exists(winget_links) and winget_links not in os.environ["PATH"]:
        os.environ["PATH"] += os.pathsep + winget_links

    # Check winget package directories for ffmpeg
    winget_pkgs = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
    if os.path.exists(winget_pkgs):
        for root, dirs, files in os.walk(winget_pkgs):
            if "ffmpeg.exe" in files:
                if root not in os.environ["PATH"]:
                    os.environ["PATH"] += os.pathsep + root
                break

setup_environment()

# App configuration persistence
CONFIG_FILE = Path(__file__).parent / "config.json"
DEFAULT_DOWNLOAD_PATH = str(Path.home() / "Downloads")

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                path = data.get("download_path", DEFAULT_DOWNLOAD_PATH)
                if os.path.isdir(path):
                    return data
        except Exception:
            pass
    return {"download_path": DEFAULT_DOWNLOAD_PATH, "quality": "🌟 بالاترین کیفیت موجود (Best)"}

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class YtDlpGui(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.config_data = load_config()
        self.is_downloading = False
        self.current_downloaded_file = None

        # Window settings
        self.title("yt-dlp Downloader")
        self.geometry("560x610")
        self.minsize(520, 580)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Set Window Icon
        icon_path = Path(__file__).parent / "app_icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        self.center_window()
        self.create_widgets()

    def center_window(self):
        self.update_idletasks()
        width = 560
        height = 610
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2) - 30
        self.geometry(f"{width}x{height}+{x}+{y}")

    def create_widgets(self):
        # Main Frame with padding
        self.main_frame = ctk.CTkFrame(self, corner_radius=15, fg_color="#1e1e24")
        self.main_frame.pack(fill="both", expand=True, padx=16, pady=16)

        # Header Title
        title_label = ctk.CTkLabel(
            self.main_frame,
            text="🎬 yt-dlp Downloader",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#ffffff"
        )
        title_label.pack(pady=(16, 2))

        subtitle_label = ctk.CTkLabel(
            self.main_frame,
            text="دانلود آسان و سریع ویدیو و موزیک با کیفیت‌های مختلف",
            font=ctk.CTkFont(size=12),
            text_color="#a0a0a8"
        )
        subtitle_label.pack(pady=(0, 16))

        # --- Section 1: URL Input ---
        url_header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        url_header_frame.pack(fill="x", padx=20, pady=(4, 4))

        ctk.CTkLabel(
            url_header_frame,
            text="🔗 آدرس ویدیو یا پلی‌لیست (URL):",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#e0e0e0"
        ).pack(side="left")

        url_input_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        url_input_frame.pack(fill="x", padx=20, pady=(0, 12))

        self.url_entry = ctk.CTkEntry(
            url_input_frame,
            placeholder_text="https://www.youtube.com/watch?v=...",
            height=38,
            font=ctk.CTkFont(size=13)
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        paste_btn = ctk.CTkButton(
            url_input_frame,
            text="📋 Paste",
            width=70,
            height=38,
            command=self.paste_url,
            fg_color="#2b2d42",
            hover_color="#3d405b"
        )
        paste_btn.pack(side="right")

        # --- Section 2: Quality Selection ---
        quality_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        quality_frame.pack(fill="x", padx=20, pady=(0, 12))

        ctk.CTkLabel(
            quality_frame,
            text="🎯 کیفیت / فرمت خروجی:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#e0e0e0"
        ).pack(anchor="w", pady=(0, 4))

        self.quality_options = [
            "🌟 بالاترین کیفیت موجود (Best Video+Audio)",
            "🎬 کیفیت 1080p (Full HD)",
            "📺 کیفیت 720p (HD)",
            "📱 کیفیت 480p (SD)",
            "🎵 فقط صدا - MP3 (High Quality 320k)",
            "🎵 فقط صدا - M4A (Original AAC)"
        ]

        saved_quality = self.config_data.get("quality", self.quality_options[0])
        if saved_quality not in self.quality_options:
            saved_quality = self.quality_options[0]

        self.quality_var = ctk.StringVar(value=saved_quality)
        self.quality_menu = ctk.CTkOptionMenu(
            quality_frame,
            values=self.quality_options,
            variable=self.quality_var,
            height=36,
            font=ctk.CTkFont(size=13),
            dropdown_font=ctk.CTkFont(size=12),
            command=self.on_quality_change
        )
        self.quality_menu.pack(fill="x")

        # --- Section 3: Save Path Selection ---
        path_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        path_frame.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkLabel(
            path_frame,
            text="📁 محل ذخیره‌سازی (Save Path):",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#e0e0e0"
        ).pack(anchor="w", pady=(0, 4))

        path_input_frame = ctk.CTkFrame(path_frame, fg_color="transparent")
        path_input_frame.pack(fill="x")

        self.path_entry = ctk.CTkEntry(
            path_input_frame,
            height=36,
            font=ctk.CTkFont(size=12)
        )
        self.path_entry.insert(0, self.config_data.get("download_path", DEFAULT_DOWNLOAD_PATH))
        self.path_entry.configure(state="readonly")
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        browse_btn = ctk.CTkButton(
            path_input_frame,
            text="📂 Browse...",
            width=85,
            height=36,
            command=self.browse_path,
            fg_color="#2b2d42",
            hover_color="#3d405b"
        )
        browse_btn.pack(side="right")

        # --- Section 4: Progress & Status Card ---
        self.status_card = ctk.CTkFrame(self.main_frame, fg_color="#141419", corner_radius=10)
        self.status_card.pack(fill="x", padx=20, pady=(0, 16), ipady=8)

        self.status_label = ctk.CTkLabel(
            self.status_card,
            text="آماده برای دانلود",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#8ecae6"
        )
        self.status_label.pack(pady=(8, 4), padx=12)

        self.progress_bar = ctk.CTkProgressBar(self.status_card, height=12, corner_radius=6)
        self.progress_bar.pack(fill="x", padx=16, pady=4)
        self.progress_bar.set(0)

        self.info_label = ctk.CTkLabel(
            self.status_card,
            text="سرعت: -- | حجم: -- | زمان باقی‌مانده: --",
            font=ctk.CTkFont(size=11),
            text_color="#8d99ae"
        )
        self.info_label.pack(pady=(2, 6))

        # --- Section 5: Action Buttons ---
        self.actions_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.actions_frame.pack(fill="x", padx=20, pady=(0, 8))

        self.download_btn = ctk.CTkButton(
            self.actions_frame,
            text="⬇️ شروع دانلود",
            height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#22577a",
            hover_color="#38a3a5",
            command=self.start_download_thread
        )
        self.download_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.open_folder_btn = ctk.CTkButton(
            self.actions_frame,
            text="📂 باز کردن پوشه",
            height=44,
            width=130,
            font=ctk.CTkFont(size=13),
            fg_color="#2b2d42",
            hover_color="#3d405b",
            command=self.open_download_folder
        )
        self.open_folder_btn.pack(side="right")

    def paste_url(self):
        try:
            clipboard = self.clipboard_get().strip()
            if clipboard:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, clipboard)
        except Exception:
            pass

    def on_quality_change(self, choice):
        self.config_data["quality"] = choice
        save_config(self.config_data)

    def browse_path(self):
        chosen = filedialog.askdirectory(initialdir=self.path_entry.get())
        if chosen:
            self.path_entry.configure(state="normal")
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, chosen)
            self.path_entry.configure(state="readonly")
            self.config_data["download_path"] = chosen
            save_config(self.config_data)

    def open_download_folder(self):
        target_dir = self.path_entry.get()
        if os.path.exists(target_dir):
            if self.current_downloaded_file and os.path.exists(self.current_downloaded_file):
                subprocess.Popen(f'explorer /select,"{self.current_downloaded_file}"')
            else:
                subprocess.Popen(f'explorer "{target_dir}"')

    def progress_hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)

            fraction = 0
            if total > 0:
                fraction = min(max(downloaded / total, 0.0), 1.0)
                pct_str = f"{fraction * 100:.1f}%"
            else:
                pct_str = d.get("_percent_str", "").strip() or "--%"

            speed_str = d.get("_speed_str", "--/s").strip()
            # Strip ANSI color codes if any
            speed_str = re.sub(r"\x1b\[[0-9;]*m", "", speed_str)
            eta_str = d.get("_eta_str", "--").strip()
            eta_str = re.sub(r"\x1b\[[0-9;]*m", "", eta_str)

            def update_ui():
                if total > 0:
                    self.progress_bar.set(fraction)
                self.status_label.configure(
                    text=f"⏳ در حال دانلود ({pct_str})...",
                    text_color="#ffd166"
                )
                self.info_label.configure(
                    text=f"سرعت: {speed_str} | زمان باقی‌مانده: {eta_str}"
                )

            self.after(0, update_ui)

        elif d["status"] == "finished":
            filename = d.get("filename")
            if filename:
                self.current_downloaded_file = filename
            def update_finish():
                self.progress_bar.set(1.0)
                self.status_label.configure(
                    text="⚙️ در حال پردازش و تبدیل با FFmpeg...",
                    text_color="#8ecae6"
                )
            self.after(0, update_finish)

    def start_download_thread(self):
        if self.is_downloading:
            return

        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("خطا", "لطفاً ابتدا لینک ویدیو را وارد کنید.")
            return

        save_path = self.path_entry.get().strip()
        if not os.path.exists(save_path):
            messagebox.showerror("خطا", "پوشه ذخیره‌سازی یافت نشد.")
            return

        self.is_downloading = True
        self.download_btn.configure(state="disabled", text="⏳ در حال دانلود...", fg_color="#555555")
        self.status_label.configure(text="🔍 در حال استخراج اطلاعات ویدیو...", text_color="#8ecae6")
        self.progress_bar.set(0)
        self.info_label.configure(text="سرعت: -- | حجم: -- | زمان باقی‌مانده: --")

        thread = threading.Thread(target=self.run_download, args=(url, save_path), daemon=True)
        thread.start()

    def run_download(self, url, save_path):
        quality_choice = self.quality_var.get()
        outtmpl = os.path.join(save_path, "%(title)s.%(ext)s")

        ydl_opts = {
            "outtmpl": outtmpl,
            "progress_hooks": [self.progress_hook],
            "quiet": True,
            "no_warnings": True,
            "windowsfilenames": True,
        }

        # Format selection based on quality choice
        if "1080p" in quality_choice:
            ydl_opts["format"] = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
        elif "720p" in quality_choice:
            ydl_opts["format"] = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        elif "480p" in quality_choice:
            ydl_opts["format"] = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
        elif "MP3" in quality_choice:
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }]
        elif "M4A" in quality_choice:
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "192",
            }]
        else:
            # Best available
            ydl_opts["format"] = "bestvideo+bestaudio/best"

        error_msg = None
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info and "_filename" in info:
                    self.current_downloaded_file = info["_filename"]
        except Exception as e:
            error_msg = str(e)

        self.after(0, lambda: self.finish_download(error_msg))

    def finish_download(self, error_msg):
        self.is_downloading = False
        self.download_btn.configure(state="normal", text="⬇️ شروع دانلود", fg_color="#22577a")

        if error_msg:
            # Clean up error text
            clean_err = re.sub(r"ERROR:\s*", "", error_msg)
            if len(clean_err) > 80:
                clean_err = clean_err[:80] + "..."
            self.status_label.configure(
                text=f"❌ خطا: {clean_err}",
                text_color="#ef476f"
            )
            self.info_label.configure(text="دانلود ناموفق بود.")
            messagebox.showerror("خطا در دانلود", f"دانلود با خطا مواجه شد:\n{error_msg}")
        else:
            self.progress_bar.set(1.0)
            self.status_label.configure(
                text="✅ دانلود با موفقیت به پایان رسید!",
                text_color="#06d6a0"
            )
            self.info_label.configure(text="فایل ذخیره شد. برای مشاهده، دکمه 'باز کردن پوشه' را بزنید.")


if __name__ == "__main__":
    app = YtDlpGui()
    app.mainloop()
