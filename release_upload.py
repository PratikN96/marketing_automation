"""
Local script — run once after stitch_cta.py.
Creates a GitHub Release and uploads all final videos as assets.
Updates queue.json with asset URLs and scheduled publish times.

Usage:
    python release_upload.py --folder final/ --start-date 2026-06-11 --skip 10
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone


QUEUE_FILE = "queue.json"
VIDEOS_PER_DAY = 3
PUBLISH_TIMES_UTC = ["13:00", "17:00", "21:00"]  # 9am, 1pm, 5pm EST


def run(cmd, check=True):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"❌ Command failed: {' '.join(cmd)}")
        print(result.stderr)
        sys.exit(1)
    return result.stdout.strip()


def build_schedule(start_date, count, skip=0):
    schedule = []
    day = start_date
    slot = 0
    total = skip + count

    all_slots = []
    while len(all_slots) < total:
        time_str = PUBLISH_TIMES_UTC[len(all_slots) % VIDEOS_PER_DAY]
        hour, minute = map(int, time_str.split(":"))
        publish_at = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
        all_slots.append(publish_at.strftime("%Y-%m-%dT%H:%M:%S.000Z"))
        if len(all_slots) % VIDEOS_PER_DAY == 0:
            day += timedelta(days=1)

    return all_slots[skip:]


def load_queue():
    if not os.path.exists(QUEUE_FILE):
        return {"pending": [], "uploaded": [], "last_updated": None}
    with open(QUEUE_FILE) as f:
        return json.load(f)


def save_queue(queue):
    queue["last_updated"] = datetime.utcnow().isoformat()
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Upload final videos to GitHub Release + update queue")
    parser.add_argument("--folder", required=True, help="Folder containing final videos")
    parser.add_argument("--start-date", required=True, help="First publish date (YYYY-MM-DD)")
    parser.add_argument("--skip", type=int, default=0, help="Skip first N videos (posted manually)")
    args = parser.parse_args()

    if not os.path.exists(args.folder):
        print(f"❌ Folder not found: {args.folder}")
        sys.exit(1)

    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")
        sys.exit(1)

    # Get repo info
    repo = run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    tag = f"week-{args.start_date}"

    videos = sorted([
        os.path.join(args.folder, f)
        for f in os.listdir(args.folder)
        if f.endswith(".mp4")
    ])

    to_upload = videos[args.skip:]

    if not to_upload:
        print("❌ No videos to upload after skip.")
        sys.exit(1)

    print(f"Creating GitHub Release: {tag}")
    print(f"Uploading {len(to_upload)} videos to release assets...\n")

    # Delete existing release with same tag if it exists
    run(["gh", "release", "delete", tag, "--repo", repo, "--yes"], check=False)
    run(["gh", "release", "create", tag, "--repo", repo,
         "--title", f"Videos {args.start_date}",
         "--notes", f"Scheduled videos starting {args.start_date}"])

    schedule = build_schedule(start_date, len(to_upload))
    asset_base = f"https://github.com/{repo}/releases/download/{tag}"

    queue = load_queue()
    # Clear old pending entries for this batch
    queue["pending"] = [v for v in queue.get("pending", []) if v.get("release_tag") != tag]

    for i, (video_path, publish_at) in enumerate(zip(to_upload, schedule), start=1):
        filename = os.path.basename(video_path)
        print(f"Uploading {i}/{len(to_upload)}: {filename}")
        run(["gh", "release", "upload", tag, video_path, "--repo", repo, "--clobber"])

        queue["pending"].append({
            "file": filename,
            "asset_url": f"{asset_base}/{filename}",
            "publish_at": publish_at,
            "release_tag": tag,
        })
        print(f"  ✅ Uploaded — scheduled {publish_at}")

    save_queue(queue)
    print(f"\n✅ queue.json updated with {len(to_upload)} pending videos.")

    # Commit and push queue.json
    run(["git", "add", QUEUE_FILE])
    run(["git", "commit", "-m", f"Queue {len(to_upload)} videos for {args.start_date}"])
    run(["git", "push"])
    print("✅ queue.json pushed to GitHub.")
    print(f"\nDone! GitHub Actions will upload 3 videos/day starting {args.start_date}.")


if __name__ == "__main__":
    main()
