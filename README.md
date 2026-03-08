# Universal Reader (Mobile-First)

A personal, offline-friendly "Universal Reader" web app that runs locally and supports private single-user workflows.

## Features
- Home screen with **Add file** (drag/drop + picker), paste text/URL, recent files list (thumbnail/icon/date).
- Supports common uploads: **PDF, DOCX, XLSX, PPTX, TXT/MD/code, PNG/JPG/SVG, MP3/WAV, SRT/VTT**.
- Every upload is stored in local **Blink Storage** (`data/blink_storage`) and linked to `private_local_user`.
- Metadata is persisted in SQLite `files`; edits are versioned in `file_versions`.
- Type-aware viewer:
  - Documents: page/preview pane + side AI drawer.
  - Text/code: editable editor with live word count.
  - Images: zoomable preview + describe/translate actions.
  - Audio: playback + streaming transcription area.
  - Unsupported: raw fallback + download.
- AI toolbelt drawer: Translate, Summarize, Edit (version save), Ask Anything.
- Global search over title, snippet, and summary.
- Offline-friendly local cache of last 10 files and AI outputs.
- Minimal mobile UI (rounded cards, soft shadows, dark/light toggle, haptic vibration).

## Run
```bash
python main.py
```
Then open `http://localhost:8000`.

## Data model
- `files`: name, size, mime, language guess, summary/snippet, storage path, timestamps.
- `file_versions`: file_id + edited content + timestamp.
