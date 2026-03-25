import os
import subprocess
import re
import json
import urllib.request
from flask import Flask, request, jsonify, send_from_directory
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

app = Flask(__name__, static_folder="static")

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

YTDLP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "bin", "yt-dlp")

sp = None


def get_spotify():
    global sp
    if sp is None:
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=os.environ.get("SPOTIPY_CLIENT_ID", ""),
            client_secret=os.environ.get("SPOTIPY_CLIENT_SECRET", "")
        ))
    return sp


def is_valid_spotify_url(url):
    return bool(re.match(r"https?://open\.spotify\.com/(track|album|playlist)/[a-zA-Z0-9]+", url))


def get_spotify_type(url):
    m = re.match(r"https?://open\.spotify\.com/(track|album|playlist)/([a-zA-Z0-9]+)", url)
    return (m.group(1), m.group(2)) if m else (None, None)


def get_tracks(url):
    stype, sid = get_spotify_type(url)
    tracks = []

    if stype == "track":
        t = get_spotify().track(sid)
        tracks.append({
            "name": t["name"],
            "artist": ", ".join(a["name"] for a in t["artists"]),
            "album": t["album"]["name"],
            "cover": t["album"]["images"][0]["url"] if t["album"]["images"] else None,
            "search": f"{t['name']} {t['artists'][0]['name']}"
        })
    elif stype == "album":
        album = get_spotify().album(sid)
        cover = album["images"][0]["url"] if album["images"] else None
        for t in album["tracks"]["items"]:
            tracks.append({
                "name": t["name"],
                "artist": ", ".join(a["name"] for a in t["artists"]),
                "album": album["name"],
                "cover": cover,
                "search": f"{t['name']} {t['artists'][0]['name']}"
            })
    elif stype == "playlist":
        results = get_spotify().playlist_tracks(sid)
        for item in results["items"]:
            t = item.get("track")
            if not t:
                continue
            tracks.append({
                "name": t["name"],
                "artist": ", ".join(a["name"] for a in t["artists"]),
                "album": t["album"]["name"],
                "cover": t["album"]["images"][0]["url"] if t["album"]["images"] else None,
                "search": f"{t['name']} {t['artists'][0]['name']}"
            })

    return tracks


def download_track(track, job_dir):
    safe_name = re.sub(r'[^\w\s\-]', '', f"{track['artist']} - {track['name']}")[:80]
    mp3_path = os.path.join(job_dir, f"{safe_name}.mp3")

    if os.path.exists(mp3_path):
        return mp3_path

    query = f"ytsearch1:{track['search']}"
    subprocess.run([
        YTDLP,
        "-x", "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", mp3_path.replace(".mp3", ".%(ext)s"),
        "--no-playlist",
        query
    ], capture_output=True, timeout=120)

    candidates = [f for f in os.listdir(job_dir) if f.startswith(safe_name) and f.endswith(".mp3")]
    return os.path.join(job_dir, candidates[0]) if candidates else None


def download_cover(cover_url, job_dir):
    if not cover_url:
        return None
    cover_path = os.path.join(job_dir, "cover.jpg")
    if not os.path.exists(cover_path):
        urllib.request.urlretrieve(cover_url, cover_path)
    return cover_path


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/info", methods=["POST"])
def info():
    data = request.get_json()
    url = data.get("url", "").strip()
    if not url or not is_valid_spotify_url(url):
        return jsonify({"error": "Ogiltig Spotify-lank"}), 400

    try:
        tracks = get_tracks(url)
        return jsonify({"tracks": tracks, "count": len(tracks)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download", methods=["POST"])
def download():
    data = request.get_json()
    url = data.get("url", "").strip()

    if not url or not is_valid_spotify_url(url):
        return jsonify({"error": "Ogiltig Spotify-lank"}), 400

    job_id = str(abs(hash(url)) % 0xFFFFFFFF)
    job_dir = os.path.join(DOWNLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    try:
        tracks = get_tracks(url)
        files = []

        # Download cover
        if tracks and tracks[0].get("cover"):
            cover_path = download_cover(tracks[0]["cover"], job_dir)
            if cover_path and os.path.exists(cover_path):
                files.append({
                    "name": "cover.jpg",
                    "path": f"/api/file/{job_id}/cover.jpg",
                    "size": os.path.getsize(cover_path),
                    "type": "cover"
                })

        # Download tracks
        for t in tracks:
            result = download_track(t, job_dir)
            if result and os.path.exists(result):
                fname = os.path.basename(result)
                files.append({
                    "name": fname,
                    "path": f"/api/file/{job_id}/{fname}",
                    "size": os.path.getsize(result),
                    "type": "audio"
                })

        if not files:
            return jsonify({"error": "Kunde inte ladda ner nagon fil"}), 500

        album_info = {
            "album": tracks[0]["album"] if tracks else "",
            "artist": tracks[0]["artist"] if tracks else "",
            "cover_url": tracks[0].get("cover") if tracks else None
        }

        return jsonify({"files": files, "job_id": job_id, "info": album_info})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/file/<job_id>/<filename>")
def serve_file(job_id, filename):
    safe_dir = os.path.join(DOWNLOAD_DIR, job_id)
    if not os.path.isdir(safe_dir):
        return jsonify({"error": "Filen hittades inte"}), 404
    return send_from_directory(safe_dir, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
