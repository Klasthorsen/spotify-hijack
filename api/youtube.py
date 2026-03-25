from http.server import BaseHTTPRequestHandler
import json
import yt_dlp


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
        except Exception:
            self._respond(400, {"error": "Ogiltig request"})
            return

        query = data.get("query", "").strip()
        if not query:
            self._respond(400, {"error": "Ingen sokfras"})
            return

        try:
            ydl_opts = {
                "format": "bestaudio/best",
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "default_search": "ytsearch1",
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                if not info or "entries" not in info or not info["entries"]:
                    self._respond(404, {"error": "Hittade ingen video"})
                    return

                entry = info["entries"][0]
                audio_url = None
                for fmt in entry.get("formats", []):
                    if fmt.get("acodec") != "none" and fmt.get("vcodec") == "none":
                        audio_url = fmt.get("url")
                        break

                if not audio_url:
                    audio_url = entry.get("url")

                self._respond(200, {
                    "title": entry.get("title", ""),
                    "video_id": entry.get("id", ""),
                    "audio_url": audio_url,
                    "thumbnail": entry.get("thumbnail", ""),
                    "duration": entry.get("duration", 0),
                    "webpage_url": entry.get("webpage_url", "")
                })

        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _respond(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
