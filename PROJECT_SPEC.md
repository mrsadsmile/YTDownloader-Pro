<USER_REQUEST>
# YTDownloader Pro — Complete UI/UX Redesign & Implementation

## ROLE & DESIGN STANDARD

Act as a Senior UI/UX Designer, Product Designer, and Desktop Application Engineer.

Your task is to completely redesign and improve the existing YTDownloader Pro desktop application.

**MANDATORY: Use the UI/UX Pro Max skill.**

Before starting:
1. Locate and read the complete UI/UX Pro Max skill instructions.
2. Apply its design system, layout, typography, accessibility, visual hierarchy, and component recommendations.
3. Use its recommendations consistently throughout the application.
4. Do not claim to have used the skill if it is unavailable.

Do not create a generic dashboard. Design a polished, production-quality desktop downloader.

---

# 1. PRODUCT SCOPE

YTDownloader Pro is a lightweight desktop video and audio downloader.

The application should focus exclusively on downloading media.

Do NOT turn this application into:
- A media library platform.
- A video editor.
- A media conversion suite.
- A complex download management system.
- A general-purpose browser.
- A statistics dashboard.

The objective is:

**Simple interface + Professional downloading capabilities + Minimal visual design.**

Keep the existing application functionality and integrate improvements without unnecessarily rewriting the download engine.

## Existing Core Technologies

Preserve the existing architecture and integrations wherever possible:

- Python
- PySide6
- yt-dlp
- FFmpeg
- SQLite, if already implemented

Do not replace working backend functionality just to change the UI.

---

# 2. DESIGN DIRECTION

## Design Style

Modern Professional Desktop Application.

Visual references:
- Premium desktop utilities.
- Minimal productivity applications.
- Professional media software.
- Modern Windows desktop applications.

Avoid:
- Cyberpunk aesthetics.
- Hacker terminal appearance.
- Neon green.
- Excessive borders.
- Excessive cards.
- Glowing buttons.
- Unnecessary gradients.
- Excessive animations.
- Decorative visual elements.

## Color Palette

Use a refined graphite and slate color system.

Dark Theme:

- Main Background: #11151B
- Secondary Background: #171D25
- Elevated Surface: #1D2530
- Input Background: #151B23
- Border: #2A3442
- Primary Text: #EDF1F7
- Secondary Text: #929DAC
- Muted Text: #687586
- Accent Blue: #718CF5
- Success: #55AE89
- Warning: #D5A451
- Error: #D76F75

Use blue only for primary actions, selected controls, and active states.

No neon colors or glow effects.

Implement a consistent color-token system rather than hardcoding colors in individual components.

## Typography

- Persian: Vazirmatn
- English: Inter
- Technical Information: JetBrains Mono

Support Persian and English properly.

Implement correct RTL and LTR layouts, not just text alignment changes.

## UI Principles

- Clear visual hierarchy.
- Consistent spacing.
- Compact but comfortable controls.
- Minimal visual noise.
- Consistent iconography.
- Professional empty states.
- Clear error messages.
- Subtle hover and focus states.
- Consistent button sizes.
- Proper keyboard accessibility.

Use Lucide icons consistently.

Do not mix random icon styles or use emojis as interface icons.

---

# 3. APPLICATION STRUCTURE

Keep the application simple.

Use a single primary Downloader page and a separate Settings page or compact Settings dialog.

Do not introduce unnecessary navigation sections.

Main Header:
- Application logo.
- YTDownloader Pro.
- Version number.
- Settings icon.
- Optional minimize-to-tray status if implemented.

Main Content:
1. URL Input.
2. Media Preview.
3. Download Configuration.
4. Download Progress.
5. Download Actions.

Settings:
- General.
- Proxy.
- Download Preferences.
- SponsorBlock.
- Engine Information.

Keep these sections compact and logically grouped.

---

# 4. MAIN DOWNLOADER PAGE

This is the most important screen.

## A. URL Input Section

Create a clean and prominent URL input.

Required features:

- URL text field.
- Paste button.
- Clear button.
- Analyze button.
- Automatic URL validation.
- Clipboard URL detection.
- Support for pasting URLs directly.
- Loading state during analysis.
- Helpful validation errors.

Placeholder:

"Paste YouTube video or playlist URL..."

Icons:
- Link
- ClipboardPaste
- Search
- X

The Analyze button should retrieve media information before downloading.

Do not start downloading automatically after analyzing a URL.

## B. Media Preview

After successful analysis, show a compact media preview.

Display:

- Video thumbnail.
- Video title.
- Channel or uploader.
- Duration.
- Source platform.
- Available resolutions.
- Available audio formats.

Do not display unnecessary metadata.

Use a horizontal layout with thumbnail on the left and information on the right.

If analysis fails, show a clear and actionable error state.

## C. Download Type Selection

Provide three simple options:

1. Video
2. Audio
3. Dual Mode

Video:
Download video with its audio.

Audio:
Extract audio and save it in the selected audio format.

Dual Mode:
Download both the video and a separate audio file.

Use compact segmented controls with appropriate Lucide icons:

- Video
- Music
- Layers

Clearly indicate the selected mode.

## D. Video Settings

Only display video-related options when Video or Dual Mode is selected.

Required options:

Video Quality:
- Best Available
- 2160p (4K)
- 1440p (2K)
- 1080p
- 720p
- 480p
- 360p

Only show qualities actually available for the selected media.

Video Format:
- MP4
- MKV
- WEBM

Frame Rate:
- Best Available
- 60 FPS
- 30 FPS

Do not offer unavailable combinations.

Use yt-dlp format selection correctly and merge audio/video streams using FFmpeg when required.

## E. Audio Settings

Only show these options when Audio or Dual Mode is selected.

Audio Format:
- MP3
- M4A
- OPUS
- WAV
- FLAC

Audio Quality:
- Best Available
- 320 kbps
- 256 kbps
- 192 kbps
- 128 kbps

Only offer meaningful quality options supported by the selected processing method.

Do not falsely imply that upscaling audio bitrate improves source quality.

## F. Download Location

Provide:

- Current download directory.
- Browse button.
- Open Folder button.

Use standard native directory selection where appropriate.

Remember the last selected directory.

Validate that the directory exists and is writable.

## G. Optional Download Settings

Place these inside a collapsed Advanced Options section.

Include:

- Embed Metadata.
- Download Thumbnail.
- Download Subtitles.
- Subtitle Language.
- Embed Subtitles.
- SponsorBlock.
- Custom Filename Template.

Do not expose technical yt-dlp arguments on the main page.

---

# 5. DOWNLOAD PROGRESS

After starting a download, display a clean progress section.

Required information:

- Current download title.
- Download status.
- Progress percentage.
- Progress bar.
- Downloaded size.
- Total size, when available.
- Current download speed.
- Estimated remaining time.
- Current operation.

Statuses:

- Ready
- Analyzing
- Waiting
- Downloading
- Merging
- Extracting Audio
- Completed
- Paused
- Cancelled
- Failed

Actions:

- Pause.
- Resume.
- Cancel.
- Retry after failure.
- Open downloaded file.
- Open download folder.

Use appropriate Lucide icons:

- Pause
- Play
- XCircle
- RefreshCw
- FolderOpen
- CheckCircle
- AlertCircle

Do not display fake progress values.

Progress must be connected to real yt-dlp and FFmpeg events.

Show a completion notification when the download finishes.

Keep technical logs hidden by default. Provide a small expandable "Technical Details" section for troubleshooting.

---

# 6. SETTINGS

Keep Settings minimal and focused exclusively on downloading.

## General

- Interface Language: English / Persian.
- Theme: Dark / Light / System.
- Default Download Location.
- Remember Last Used Settings.
- Show Desktop Notifications.
- Minimize to System Tray, if supported.

## Proxy Settings

Preserve the existing proxy functionality.

Options:

- Enable Proxy.
- Proxy Protocol.
- Proxy Address.
- Port.
- Username.
- Password.
- Test Connection.

Preserve existing presets:

- V2Ray
- V2Ray SOCKS
- Clash
- Sing-box

Validate proxy input.

Show connection results:

- Connected.
- Connection Failed.
- Timeout.
- Invalid Configuration.

Do not expose passwords in logs.

Do not assume a local proxy is running just because an address has been entered.

## Download Preferences

- Default Download Type.
- Default Video Quality.
- Default Video Format.
- Default Audio Format.
- Default Audio Quality.
- Default Download Folder.
- Filename Template.
- Duplicate File Behavior.
- Maximum Concurrent Downloads, if supported by the current engine.

## SponsorBlock

Preserve the existing SponsorBlock functionality.

Provide a simple enable/disable toggle.

Optional category selection:

- Sponsor
- Self Promotion
- Interaction Reminder
- Intro
- Outro
- Filler

Only expose categories that are actually supported by the implementation.

## Engine Information

Display:

- yt-dlp version.
- FFmpeg version.
- Application version.
- Engine status.
- Check for yt-dlp updates.
- Update yt-dlp.
- Check FFmpeg availability.

Keep this section informational and compact.

---

# 7. ESSENTIAL FUNCTIONAL FEATURES

Only implement features that directly improve the downloading experience.

Mandatory:

1. Video URL analysis.
2. Thumbnail and metadata preview.
3. Dynamic available-quality detection.
4. Video downloading.
5. Audio extraction.
6. Dual Mode downloading.
7. MP4 / MKV / WEBM support where available.
8. MP3 / M4A / OPUS / WAV / FLAC support.
9. Download progress.
10. Real-time download speed.
11. Estimated remaining time.
12. Pause and Resume where supported.
13. Cancel download.
14. Retry failed downloads.
15. Custom download directory.
16. Clipboard Paste.
17. Automatic URL validation.
18. Duplicate filename handling.
19. Subtitle downloading.
20. SponsorBlock integration.
21. Proxy support.
22. yt-dlp update checking.
23. FFmpeg availability checking.
24. Clear error handling.
25. Download completion notification.

Optional but useful:

- Playlist URL recognition.
- Basic playlist download.
- Multiple URL input.
- Remember previous download preferences.
- Open downloaded file.
- Open download directory.

Do not implement advanced features outside this scope.

---

# 8. ERROR HANDLING

Create user-friendly error messages.

Examples:

Invalid URL:
"Please enter a valid supported media URL."

Network Error:
"Unable to connect to the source. Check your internet or proxy settings."

Proxy Error:
"Proxy connection failed. Verify your proxy configuration."

Unavailable Media:
"This media is currently unavailable."

FFmpeg Missing:
"FFmpeg is missing or unavailable. Check your installation."

Disk Error:
"Unable to save the file. Check your download directory and available storage."

Download Failed:
"Download failed. You can retry or view technical details."

Provide Retry and View Details actions when relevant.

Preserve the original technical error in the diagnostic logs.

---

# 9. ICON SYSTEM

Use Lucide icons consistently.

Recommended icons:

Application:
- Download
- Settings
- Info

URL:
- Link
- ClipboardPaste
- Search
- X

Media:
- Video
- Music
- Layers
- Image
- Clock
- User
- MonitorPlay

Download:
- Download
- Pause
- Play
- XCircle
- RefreshCw
- CheckCircle
- AlertCircle

Files:
- Folder
- FolderOpen
- FileVideo
- FileAudio

Settings:
- Globe
- Moon
- Sun
- Monitor
- Shield
- Network
- Zap
- HardDrive

System:
- Activity
- Terminal
- Info
- RefreshCw

Use icon-only buttons only when the action is universally recognizable. Add tooltips to icon-only controls.

---

# 10. MICROINTERACTIONS

Use subtle and functional animations only.

- Smooth hover states.
- Button press feedback.
- Loading spinner during analysis.
- Subtle progress animation.
- Smooth appearance of media preview.
- Clear success and error states.
- No continuous decorative animations.
- No glowing effects.
- No excessive transitions.

Respect reduced-motion preferences where possible.

---

# 11. RESPONSIVENESS AND ACCESSIBILITY

Although this is a desktop application:

- Support window resizing.
- Maintain correct layout at different resolutions.
- Avoid horizontal overflow.
- Support Windows display scaling.
- Maintain readable typography.
- Provide keyboard navigation.
- Provide visible focus states.
- Ensure sufficient contrast.
- Support proper Persian RTL layouts.
- Keep controls large enough to interact with comfortably.

---

# 12. ENGINEERING REQUIREMENTS

Do not compromise existing download functionality.

- Keep yt-dlp as the download engine.
- Use FFmpeg for merging and audio processing.
- Run long-running operations outside the GUI thread.
- Keep the interface responsive during downloads.
- Use signals and slots correctly in PySide6.
- Avoid blocking the main UI thread.
- Handle subprocess termination safely.
- Handle application shutdown during active downloads.
- Preserve settings between sessions.
- Do not expose sensitive proxy credentials.
- Validate user input.
- Avoid duplicate download jobs.
- Handle temporary files correctly.
- Never report success before verifying the output file.

Use existing project architecture whenever practical.

Do not create unnecessary abstractions or introduce additional dependencies without a clear reason.

---

# 13. FINAL DESIGN QUALITY REQUIREMENTS

The final application must feel like a polished commercial desktop utility.

It should be:

- Minimal.
- Professional.
- Fast.
- Clean.
- Consistent.
- Intuitive.
- Lightweight.
- Technically reliable.

The main downloader page must be understandable immediately without documentation.

A first-time user should be able to:

1. Paste a URL.
2. Analyze the media.
3. Select Video, Audio, or Dual Mode.
4. Choose quality and format.
5. Select the destination folder.
6. Start downloading.
7. Monitor progress.
8. Open the completed file.

All without navigating through unnecessary screens.

---

# 14. IMPLEMENTATION WORKFLOW

Follow this sequence:

Phase 1:
Inspect the existing codebase, architecture, components, and download engine.

Phase 2:
Identify existing functionality that must be preserved.

Phase 3:
Apply UI/UX Pro Max design recommendations and establish design tokens.

Phase 4:
Redesign the main downloader screen.

Phase 5:
Redesign the settings interface.

Phase 6:
Connect every UI control to actual backend functionality.

Phase 7:
Test all download modes, format selection, proxy settings, progress reporting, and error states.

Phase 8:
Verify that the application works correctly at different window sizes.

Phase 9:
Remove obsolete UI elements and unused components.

Phase 10:
Deliver a fully working application, not just a visual mockup.

IMPORTANT:
Do not stop after creating a static UI prototype.

Do not replace real functionality with fake buttons, sample progress bars, or placeholder interactions.

Do not invent unsupported capabilities.

Do not add features outside the defined product scope without explicit approval.

Before finishing, provide a concise summary of:
- What changed.
- Which features were implemented.
- Which existing features were preserved.
- Which tests passed.
- Any remaining limitations.

**FINAL OBJECTIVE: Build a minimal, elegant, fast, and reliable YouTube downloader with professional UX and no unnecessary complexity.**
</USER_REQUEST>
<ADDITIONAL_METADATA>
The current local time is: 2026-11-24T12:36:45+03:30.
</ADDITIONAL_METADATA>