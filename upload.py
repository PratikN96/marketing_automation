"""
Step 3: Upload final videos to YouTube with scheduled publish times.
Uploads all videos in final/ as private, scheduled 3/day starting from --start-date.

Usage:
    python upload.py --folder final/ --start-date 2026-06-08
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


QUEUE_FILE = "queue.json"
VIDEOS_PER_DAY = 3
# Publish times in UTC (13:00, 17:00, 21:00 = 9am, 1pm, 5pm EST)
PUBLISH_TIMES_UTC = ["13:00", "17:00", "21:00"]


def get_youtube_client():
    client_id     = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        print("❌ Missing YouTube credentials. Set these env vars:")
        print("   YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN")
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
    if not os.path.exists(QUEUE_FILE):
        return {"pending": [], "uploaded": [], "last_updated": None}
    with open(QUEUE_FILE) as f:
        return json.load(f)


def save_queue(queue):
    queue["last_updated"] = datetime.utcnow().isoformat()
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def build_schedule(start_date, count):
    """Generate a list of ISO8601 publish times for `count` videos."""
    schedule = []
    day = start_date
    slot = 0

    while len(schedule) < count:
        time_str = PUBLISH_TIMES_UTC[slot % VIDEOS_PER_DAY]
        hour, minute = map(int, time_str.split(":"))
        publish_at = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
        schedule.append(publish_at.strftime("%Y-%m-%dT%H:%M:%S.000Z"))
        slot += 1
        if slot % VIDEOS_PER_DAY == 0:
            day += timedelta(days=1)

    return schedule


def upload_video(youtube, video_path, publish_at, index, total):
    filename = os.path.basename(video_path)
    title = f"#{index:03d}"  # Update in config.py for custom titles

    body = {
        "snippet": {
            "title": title,
            "description": "",
            "tags": [],
            "categoryId": "22",
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": publish_at,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)

    print(f"Uploading {index}/{total}: {filename} → scheduled {publish_at}")

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"  {pct}% uploaded...", end="\r")

    print(f"  ✅ Uploaded: youtube.com/watch?v={response['id']}")
    return response["id"]


def main():
    parser = argparse.ArgumentParser(description="Upload final videos to YouTube")
    parser.add_argument("--folder", required=True, help="Folder containing final videos")
    parser.add_argument("--start-date", required=True, help="First publish date (YYYY-MM-DD)")
    args = parser.parse_args()

    if not os.path.exists(args.folder):
        print(f"❌ Folder not found: {args.folder}")
        sys.exit(1)

    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")
        sys.exit(1)

    # Load queue
    queue = load_queue()
    already_uploaded = set(v["file"] for v in queue.get("uploaded", []))

    # Find videos to upload
    videos = sorted([
        os.path.join(args.folder, f)
        for f in os.listdir(args.folder)
        if f.endswith(".mp4")
    ])

    pending = [v for v in videos if v not in already_uploaded]

    if not pending:
        print("✅ All videos already uploaded. Nothing to do.")
        sys.exit(0)

    print(f"Found {len(pending)} videos to upload.")
    print(f"Scheduling {VIDEOS_PER_DAY}/day starting {args.start_date}\n")

    schedule = build_schedule(start_date, len(pending))
    youtube = get_youtube_client()

    for i, (video_path, publish_at) in enumerate(zip(pending, schedule), start=1):
        try:
            video_id = upload_video(youtube, video_path, publish_at, i, len(pending))
            queue["uploaded"].append({
                "file": video_path,
                "youtube_id": video_id,
                "publish_at": publish_at,
                "uploaded_at": datetime.utcnow().isoformat(),
            })
            save_queue(queue)
        except Exception as e:
            print(f"  ❌ Failed to upload {video_path}: {e}")
            # Save progress so far before continuing
            save_queue(queue)

    total_uploaded = len([v for v in queue["uploaded"] if v["file"] in set(v["file"] for v in queue["uploaded"])])
    print(f"\nDone. {len(pending)} videos uploaded and scheduled.")
    print(f"Queue saved to {QUEUE_FILE}")


if __name__ == "__main__":
    main()
