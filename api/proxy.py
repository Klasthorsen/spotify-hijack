from http.server import BaseHTTPRequestHandler
import os
import urllib.parse
import yt_dlp
import uuid


TMP = "/tmp"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        query = params.get("q", [""])[0]

        if not query:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing ?q= parameter")
            return

        job_id = uuid.uuid4().hex[:8]
        out_template = os.path.join(TMP, f"{job_id}.%(ext)s")
        out_mp3 = os.path.join(TMP, f"{job_id}.mp3")

        try:
            ydl_opts = {
                "format": "bestaudio/best",
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "default_search": "ytsearch1",
                "outtmpl": out_template,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }

            title = "audio"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=True)
                if info and "entries" in info and info["entries"]:
                    title = info["entries"][0].get("title", "audio")

            if not os.path.exists(out_mp3):
                candidates = [f for f in os.listdir(TMP) if f.startswith(job_id)]
                if candidates:
                    out_mp3 = os.path.join(TMP, candidates[0])
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"Download failed")
                    return

            safe_title = "".join(c for c in title if c.isalnum() or c in " -_")[:80]
            file_size = os.path.getsize(out_mp3)

            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Content-Length", str(file_size))
            self.send_header("Content-Disposition", f'attachment; filename="{safe_title}.mp3"')
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            with open(out_mp3, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(str(e).encode())
        finally:
            for f in os.listdir(TMP):
                if f.startswith(job_id):
                    try:
                        os.remove(os.path.join(TMP, f))
                    except:
                        pass
