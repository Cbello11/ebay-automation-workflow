from __future__ import annotations

import json
import mimetypes
import os
import re
import sqlite3
import uuid
import zipfile
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BLINK_STORAGE_DIR = DATA_DIR / "blink_storage"
DB_PATH = DATA_DIR / "app.db"
SINGLE_USER_ID = "private_local_user"

TEXT_EXTENSIONS = {".txt", ".md", ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml", ".html", ".css", ".java", ".c", ".cpp", ".go", ".rs", ".php", ".rb", ".sh", ".sql", ".srt", ".vtt"}


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BLINK_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS files (id TEXT PRIMARY KEY,user_id TEXT,name TEXT,size INTEGER,mime TEXT,type_group TEXT,language_guess TEXT,summary TEXT,content_snippet TEXT,storage_path TEXT,created_at TEXT,last_opened_at TEXT,thumbnail TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS file_versions (id TEXT PRIMARY KEY,file_id TEXT,content TEXT,created_at TEXT)""")
    conn.commit(); conn.close()


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_filename(name: str) -> str:
    return re.sub(r"[^\w.\- ]", "_", name).strip() or "untitled"


def guess_language(text: str) -> str:
    if re.search(r"[\u3040-\u30ff]", text): return "ja"
    if re.search(r"[\u4e00-\u9fff]", text): return "zh"
    low = f" {text.lower()} "
    if any(t in low for t in [" the ", " and ", " is "]): return "en"
    if any(t in low for t in [" el ", " la ", " de "]): return "es"
    return "unknown"


def file_type_group(name: str, mime: str) -> str:
    ext = Path(name).suffix.lower()
    if mime.startswith("image/") or ext in {".png", ".jpg", ".jpeg", ".svg"}: return "image"
    if mime.startswith("audio/") or ext in {".mp3", ".wav"}: return "audio"
    if ext in {".pdf", ".docx", ".xlsx", ".pptx"}: return "document"
    if ext in TEXT_EXTENSIONS: return "text"
    return "raw"


def extract_office_text(path: Path, ext: str) -> str:
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            if ext == ".docx": names = ["word/document.xml"]
            elif ext == ".pptx": names = [n for n in names if n.startswith("ppt/slides/slide")]
            elif ext == ".xlsx": names = [n for n in names if n.startswith("xl/sharedStrings") or n.startswith("xl/worksheets/sheet")]
            out = []
            for n in names:
                try: out.append(re.sub(r"<[^>]+>", " ", zf.read(n).decode("utf-8", errors="ignore")))
                except KeyError: pass
            return "\n".join(out)
    except Exception:
        return ""


def read_text_content(path: Path, name: str) -> str:
    ext = Path(name).suffix.lower()
    if ext in TEXT_EXTENSIONS: return path.read_text(encoding="utf-8", errors="ignore")
    if ext in {".docx", ".xlsx", ".pptx"}: return extract_office_text(path, ext)
    return ""


def summarize_text(text: str) -> dict:
    clean = " ".join(text.split())
    if not clean: return {"paragraph": "No extractable text.", "bullets": ["• Upload another file or use Ask Anything."]}
    paragraph = clean[:220] + ("..." if len(clean) > 220 else "")
    bullets = [f"• {x[:110]}" for x in re.split(r"[.!?]", clean) if x.strip()][:3] or ["• Content loaded."]
    return {"paragraph": paragraph, "bullets": bullets}


class AppHandler(BaseHTTPRequestHandler):
    def _json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def _serve_file(self, path: Path, ctype: str | None = None):
        if not path.exists():
            self.send_error(404); return
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype or mimetypes.guess_type(str(path))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers(); self.wfile.write(content)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/": return self._serve_file(BASE_DIR / "templates" / "index.html", "text/html")
        if parsed.path.startswith("/static/"):
            return self._serve_file(BASE_DIR / parsed.path.lstrip("/"))
        if parsed.path == "/api/files":
            conn = get_db(); rows = conn.execute("SELECT * FROM files WHERE user_id=? ORDER BY last_opened_at DESC LIMIT 30", (SINGLE_USER_ID,)).fetchall(); conn.close()
            return self._json([dict(r) for r in rows])
        if parsed.path == "/api/search":
            q = (parse_qs(parsed.query).get("q", [""])[0]).strip().lower()
            if not q: return self._json([])
            conn = get_db(); rows = conn.execute("SELECT * FROM files WHERE user_id=? AND (lower(name) LIKE ? OR lower(ifnull(content_snippet,'')) LIKE ? OR lower(ifnull(summary,'')) LIKE ?) ORDER BY last_opened_at DESC LIMIT 30", (SINGLE_USER_ID, f"%{q}%", f"%{q}%", f"%{q}%")).fetchall(); conn.close()
            return self._json([dict(r) for r in rows])
        m = re.match(r"^/api/files/([\w-]+)$", parsed.path)
        if m:
            fid = m.group(1)
            conn = get_db(); row = conn.execute("SELECT * FROM files WHERE id=?", (fid,)).fetchone()
            if not row: conn.close(); return self._json({"error": "File not found"}, 404)
            conn.execute("UPDATE files SET last_opened_at=? WHERE id=?", (now_iso(), fid)); conn.commit(); conn.close()
            info = dict(row); info["content"] = read_text_content(Path(info["storage_path"]), info["name"])
            return self._json(info)
        m = re.match(r"^/api/files/([\w-]+)/download$", parsed.path)
        if m:
            conn = get_db(); row = conn.execute("SELECT * FROM files WHERE id=?", (m.group(1),)).fetchone(); conn.close()
            if not row: return self._json({"error": "File not found"}, 404)
            path = Path(row["storage_path"])
            if not path.exists(): return self._json({"error": "Missing file"}, 404)
            content = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", row["mime"])
            self.send_header("Content-Disposition", f'attachment; filename="{row["name"]}"')
            self.send_header("Content-Length", str(len(content)))
            self.end_headers(); self.wfile.write(content); return
        self.send_error(404)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode() or "{}")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/upload":
            ctype = self.headers.get("Content-Type", "")
            m = re.search(r"boundary=(.+)", ctype)
            if not m: return self._json({"error": "Invalid multipart"}, 400)
            boundary = ("--" + m.group(1)).encode()
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            parts = raw.split(boundary)
            filename, file_content = "upload.bin", b""
            for part in parts:
                if b"filename=" in part:
                    header, body = part.split(b"\r\n\r\n", 1)
                    match = re.search(br'filename="([^"]+)"', header)
                    if match: filename = normalize_filename(match.group(1).decode(errors="ignore"))
                    file_content = body.rsplit(b"\r\n", 1)[0]
                    break
            if not file_content: return self._json({"error": "No file"}, 400)
            fid = str(uuid.uuid4())
            user_dir = BLINK_STORAGE_DIR / SINGLE_USER_ID; user_dir.mkdir(parents=True, exist_ok=True)
            save_path = user_dir / f"{fid}_{filename}"; save_path.write_bytes(file_content)
            mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            tgroup = file_type_group(filename, mime)
            text = read_text_content(save_path, filename)
            conn = get_db(); conn.execute("INSERT INTO files VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (fid, SINGLE_USER_ID, filename, len(file_content), mime, tgroup, guess_language(text), summarize_text(text)["paragraph"] if text else "", text[:2000], str(save_path), now_iso(), now_iso(), "")); conn.commit(); conn.close()
            return self._json({"id": fid})
        if parsed.path == "/api/paste":
            payload = self._read_json(); text = (payload.get("text") or "").strip()
            if not text: return self._json({"error": "No text"}, 400)
            fid = str(uuid.uuid4())
            url = urlparse(text)
            name = normalize_filename((url.netloc + url.path).strip("/") + ".txt") if url.scheme in {"http", "https"} else "pasted_text.txt"
            content = f"URL: {text}" if url.scheme in {"http", "https"} else text
            user_dir = BLINK_STORAGE_DIR / SINGLE_USER_ID; user_dir.mkdir(parents=True, exist_ok=True)
            save_path = user_dir / f"{fid}_{name}"; save_path.write_text(content, encoding="utf-8")
            s = summarize_text(content)
            conn = get_db(); conn.execute("INSERT INTO files VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (fid, SINGLE_USER_ID, name, save_path.stat().st_size, "text/plain", "text", guess_language(content), s["paragraph"], content[:2000], str(save_path), now_iso(), now_iso(), "")); conn.commit(); conn.close()
            return self._json({"id": fid})
        if parsed.path == "/api/ai/translate":
            p = self._read_json(); txt = p.get("text", ""); target = p.get("target", "en")
            source = guess_language(txt)
            return self._json({"source": source, "target": target, "translated": f"[{source}→{target}] {txt}"})
        if parsed.path == "/api/ai/summarize":
            return self._json(summarize_text(self._read_json().get("text", "")))
        if parsed.path == "/api/ai/ask":
            p = self._read_json(); q = p.get("question", "")
            return self._json({"answer": f"Based on loaded text, answer draft: {q}" if q else "Ask a question about this file."})
        if parsed.path == "/api/ai/edit":
            p = self._read_json(); fid = p.get("file_id"); content = p.get("content", "")
            if not fid: return self._json({"error": "file_id required"}, 400)
            vid = str(uuid.uuid4())
            conn = get_db(); conn.execute("INSERT INTO file_versions VALUES (?,?,?,?)", (vid, fid, content, now_iso())); conn.execute("UPDATE files SET content_snippet=?, summary=?, last_opened_at=? WHERE id=?", (content[:2000], summarize_text(content)["paragraph"], now_iso(), fid)); conn.commit(); conn.close()
            return self._json({"version_id": vid})
        self.send_error(404)


def run_server(host="0.0.0.0", port=8000):
    init_db()
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Universal Reader running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
