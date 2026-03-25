import json
import yt_dlp


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

    query = body.get("query", "").strip()
    if not query:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Ingen sokfras"})
        }

    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "default_search": "ytsearch1",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if not info or "entries" not in info or not info["entries"]:
                return {
                    "statusCode": 404,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Hittade ingen video"})
                }

            entry = info["entries"][0]
            audio_url = None
            for fmt in entry.get("formats", []):
                if fmt.get("acodec") != "none" and fmt.get("vcodec") == "none":
                    audio_url = fmt.get("url")
                    break

            if not audio_url:
                audio_url = entry.get("url")

            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "title": entry.get("title", ""),
                    "video_id": entry.get("id", ""),
                    "audio_url": audio_url,
                    "thumbnail": entry.get("thumbnail", ""),
                    "duration": entry.get("duration", 0),
                    "webpage_url": entry.get("webpage_url", "")
                })
            }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
