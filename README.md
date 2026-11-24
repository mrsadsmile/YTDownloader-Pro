# YTDownloader Pro

A modern, minimal desktop utility for downloading video and audio streams, built with Python and PySide6.

## Features

- Clean, modern desktop interface built with PySide6 and styled in dark graphite tones.
- Media inspection with thumbnail, channel, and resolution preview.
- Three download modes: Video, Audio Only, and Dual Mode (simultaneous video and MP3 extraction).
- Dynamic quality selection based on available source resolutions.
- Proxy and network configuration support (HTTP and SOCKS5).
- Integrated FFmpeg support for stream merging and high-bitrate audio extraction.
- Desktop notifications and progress tracking with real-time speed and ETA.

## Acknowledgments & Credits

This project utilizes and is powered by open-source technologies:
- **yt-dlp** ([https://github.com/yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp)): The core extraction engine used for media analysis and downloads.
- **FFmpeg** ([https://ffmpeg.org](https://ffmpeg.org)): Used for multimedia post-processing, remuxing, and audio format conversion.

## Requirements & Building from Source

```bash
pip install -r requirements.txt
python YTDownloader.pyw
```

## Binary Installer

A standalone Windows installer (`YTDownloader_Setup_by_AliCH.exe`) is available under the Releases section, requiring no external Python or FFmpeg installation.

## License

MIT License. Designed and packaged by AliCH.
