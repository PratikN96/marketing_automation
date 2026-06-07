"""
Runs on GitHub Actions daily.
Picks next 3 pending videos from queue.json, downloads from GitHub Release,
uploads to YouTube with scheduled publish times, updates queue.json.
"""

import json
import os
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone

import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

import config


QUEUE_FILE = "queue.json"
VIDEOS_PER_RUN = 3


def get_youtube_client():
    client_id     = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        print("❌ Missing YouTube credentials in environment.")
        sys.exit(1)

    creds = google.oauth2.credentials.Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("youtube", "v3", credentials=creds)


def load_queue():
    with open(QUEUE_FILE) as f:
        return json.load(f)


def save_queue(queue):
    queue["last_updated"] = datetime.utcnow().isoformat()
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def download_asset(url, dest_path):
    github_token = os.environ.get("GITHUB_TOKEN", "")
    req = urllib.request.Request(url)
    if github_token:
        req.add_header("Authorization", f"token {github_token}")
    req.add_header("Accept", "application/octet-stream")
    with urllib.request.urlopen(req) as response, open(dest_path, "wb") as f:
        f.write(response.read())


def upload_video(youtube, video_path, publish_at, filename):
    body = {
        "snippet": {
            "title": filename.replace(".mp4", "").replace("_", " "),
            "description": config.VIDEO_DESCRIPTION,
            "tags": config.VIDEO_TAGS,
            "categoryId": config.VIDEO_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": publish_at,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  {int(status.progress() * 100)}% uploaded...", end="\r")

    print(f"  ✅ Uploaded: youtube.com/watch?v={response['id']} → {publish_at}")
    return response["id"]


def main():
    if not os.path.exists(QUEUE_FILE):
        print("❌ queue.json not found.")
        sys.exit(1)

    queue = load_queue()
    pending = queue.get("pending", [])

    if not pending:
        print("✅ No pending videos. Nothing to upload today.")
        sys.exit(0)

    batch = pending[:VIDEOS_PER_RUN]
    print(f"Uploading {len(batch)} videos today ({len(pending)} pending total)\n")

    youtube = get_youtube_client()

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, item in enumerate(batch, start=1):
            filename = item["file"]
            asset_url = item["asset_url"]
            publish_at = item["publish_at"]

            print(f"[{i}/{len(batch)}] {filename} → {publish_at}")
            dest = os.path.join(tmpdir, filename)

            print(f"  Downloading from GitHub Release...")
            try:
                download_asset(asset_url, dest)
            except Exception as e:
                print(f"  ❌ Download failed: {e}")
                continue

            try:
                video_id = upload_video(youtube, dest, publish_at, filename)
                # Move from pending to uploaded
                queue["pending"].remove(item)
                queue.setdefault("uploaded", []).append({
                    "file": filename,
                    "youtube_id": video_id,
                    "publish_at": publish_at,
                    "uploaded_at": datetime.utcnow().isoformat(),
                })
                save_queue(queue)
            except Exception as e:
                print(f"  ❌ Upload failed: {e}")

    remaining = len(queue.get("pending", []))
    print(f"\nDone. {remaining} videos still pending in queue.")


if __name__ == "__main__":
    main()
