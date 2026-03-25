from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import yt_dlp


def extract_audio_url(query):
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch1",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=False)
        if not info or "entries" not in info or not info["entries"]:
            return None, None
        entry = info["entries"][0]
        # Prefer audio-only format
        for fmt in sorted(entry.get("formats", []), key=lambda f: f.get("abr", 0) or 0, reverse=True):
            if fmt.get("acodec") != "none" and fmt.get("vcodec") in ("none", None):
                return fmt.get("url"), entry.get("title", "audio")
        return entry.get("url"), entry.get("title", "audio")


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        query = params.get("q", [""])[0]

        if not query:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing ?q= parameter")
            return

        try:
            audio_url, title = extract_audio_url(query)
            if not audio_url:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found")
                return

            req = urllib.request.Request(audio_url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=30)

            safe_title = "".join(c for c in title if c.isalnum() or c in " -_")[:80]
            content_type = resp.headers.get("Content-Type", "audio/mp4")

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Disposition", f'attachment; filename="{safe_title}.m4a"')
            self.send_header("Access-Control-Allow-Origin", "*")
            if resp.headers.get("Content-Length"):
                self.send_header("Content-Length", resp.headers.get("Content-Length"))
            self.end_headers()

            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(str(e).encode())
