# YTDownloader Pro

A modern, minimal desktop utility for downloading video and audio streams, built with Python and PySide6.

> [!NOTE]
> **A Note from the Author:**  
> I am a **vibe coder**, not a professional software developer or programmer! I designed and built this clean desktop UI/UX and integrated these features with the assistance of **Gemini 3.8 Flash High** (Google Antigravity AI).  
> If you test the program or review the source code and notice any bugs, inefficiencies, or areas for improvement, please open an [Issue](https://github.com/mrsadsmile/YTDownloader-Pro/issues) or share your feedback so I can learn and improve!

---

## 🌟 Core Engine & Acknowledgments

This application is purely a graphical desktop user interface (GUI). All core video/audio extraction, streaming mechanics, and multimedia conversions are powered by the incredible open-source projects below. Full credit goes to their original creators and contributors:

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**: The world-class command-line audio/video downloader. All stream parsing, resolution detection, and downloading logic are powered by yt-dlp.
- **[FFmpeg](https://ffmpeg.org)**: The leading multimedia framework used for stream remuxing, merging separate video/audio streams, and high-quality audio extraction.
- **[PySide6 / Qt](https://www.qt.io)**: Official Python bindings for Qt, providing a native, hardware-accelerated desktop experience.
- **[Lucide](https://lucide.dev)**: Beautiful & consistent open-source vector icons.

---

## Features

- **Modern Desktop UI/UX**: Designed with a refined dark graphite & slate palette.
- **Live Media Inspection**: URL auto-detection, video thumbnail, channel name, duration, and dynamically detected resolutions.
- **Three Download Modes**:
  - **Video**: Downloads video with audio merged into MP4/MKV/WEBM.
  - **Audio Only**: Direct extraction to MP3, M4A, OPUS, FLAC, or WAV.
  - **Dual Mode**: Downloads the full-quality video and extracts a separate high-bitrate MP3 simultaneously.
- **Smart Quality Selector**: Displays only resolutions actually available for the analyzed media (from 360p up to 4K).
- **Network & Proxy Support**: Built-in support for HTTP and SOCKS5 proxies with pre-configured presets (V2Ray, Clash, Sing-Box) and a live latency/connection tester.
- **Clean Progress Tracking**: Real-time download speed, ETA, downloaded size, and total size without fake numbers.
- **Windows Path & Junction Protection**: Sanitizes environment variables to prevent `WinError 448` on Windows systems with custom user directory junctions.

---

## Running from Source

```bash
git clone https://github.com/mrsadsmile/YTDownloader-Pro.git
cd YTDownloader-Pro
pip install -r requirements.txt
python YTDownloader.pyw
```

---

## Windows Standalone Installer

A portable Windows installer (`YTDownloader_Setup.exe`) is available under the [Releases](https://github.com/mrsadsmile/YTDownloader-Pro/releases) page. It bundles Python, PySide6, yt-dlp, FFmpeg, and fonts with zero external dependencies required.

---

## License

Open source under the [MIT License](LICENSE).
