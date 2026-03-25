import os
import re
import json
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

sp = None


def get_spotify():
    global sp
    if sp is None:
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=os.environ.get("SPOTIPY_CLIENT_ID", ""),
            client_secret=os.environ.get("SPOTIPY_CLIENT_SECRET", "")
        ))
    return sp


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


def handler(request):
    if request.method == "OPTIONS":
        return {"statusCode": 200, "body": ""}

    try:
        body = json.loads(request.body)
    except Exception:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Ogiltig request"})
        }

    url = body.get("url", "").strip()
    if not url or not re.match(r"https?://open\.spotify\.com/(track|album|playlist)/[a-zA-Z0-9]+", url):
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Ogiltig Spotify-lank"})
        }

    try:
        tracks = get_tracks(url)
        album_info = {}
        if tracks:
            album_info = {
                "album": tracks[0]["album"],
                "artist": tracks[0]["artist"],
                "cover_url": tracks[0].get("cover")
            }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"tracks": tracks, "count": len(tracks), "info": album_info})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
