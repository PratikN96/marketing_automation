"""
Step 1: Scrape hooks from a YouTube Shorts channel.
Downloads the first 3 seconds of the most recent N videos.

Usage:
    python scrape_hooks.py --channel "https://www.youtube.com/@ZackDFilms/shorts" --count 25
"""

import argparse
import os
import subprocess
import sys

import yt_dlp


HOOKS_DIR = "hooks"
DOWNLOADED_LOG = "downloaded_urls.txt"
FAILED_LOG = "failed_downloads.txt"


def load_set(filepath):
    if not os.path.exists(filepath):
        return set()
    with open(filepath) as f:
        return set(line.strip() for line in f if line.strip())


def append_line(filepath, line):
    with open(filepath, "a") as f:
        f.write(line + "\n")


def fetch_video_urls(channel_url, count):
    # Ensure we hit the /shorts tab
    if "/shorts" not in channel_url:
        channel_url = channel_url.rstrip("/") + "/shorts"

    print(f"Fetching last {count} video URLs from {channel_url} ...")
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "playlist_end": count,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)
        entries = info.get("entries", [])
        urls = []
        for entry in entries:
            if not entry:
                continue
            # Video IDs are exactly 11 characters
            vid_id = entry.get("id", "")
            if vid_id and len(vid_id) == 11:
                urls.append("https://www.youtube.com/watch?v=" + vid_id)
        return urls


def download_3s_clip(url, output_path):
    """Download full video then trim to 3 seconds using ffmpeg."""
    tmp_path = output_path + ".tmp.mp4"

    ydl_opts = {
        "quiet": True,
        "outtmpl": tmp_path,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "extractor_args": {"youtube": {"player_client": ["android"]}},
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Trim to first 3 seconds, force vertical 1080x1920
    cmd = [
        "ffmpeg", "-y",
        "-i", tmp_path,
        "-t", "3",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
        "-c:a", "aac", "-ar", "44100",
        "-movflags", "+faststart",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True)

    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode())


def main():
    parser = argparse.ArgumentParser(description="Scrape YouTube Shorts hooks")
    parser.add_argument("--channel", required=True, help="YouTube channel or shorts URL")
    parser.add_argument("--count", type=int, default=25, help="Number of videos to scrape")
    args = parser.parse_args()

    os.makedirs(HOOKS_DIR, exist_ok=True)

    already_downloaded = load_set(DOWNLOADED_LOG)
    urls = fetch_video_urls(args.channel, args.count)

    if not urls:
        print("No videos found. Check the channel URL.")
        sys.exit(1)

    print(f"Found {len(urls)} videos. Starting download...\n")

    # Determine starting index from existing hooks
    existing = [f for f in os.listdir(HOOKS_DIR) if f.endswith(".mp4")]
    start_index = len(existing) + 1

    success_count = 0
    for i, url in enumerate(urls, start=1):
        if url in already_downloaded:
            print(f"Skipping {i}/{len(urls)} (already downloaded): {url}")
            continue

        index = start_index + success_count
        output_path = os.path.join(HOOKS_DIR, f"hook_{index:03d}.mp4")

        print(f"Downloading {i}/{len(urls)}: {url}")
        try:
            download_3s_clip(url, output_path)
            append_line(DOWNLOADED_LOG, url)
            success_count += 1
            print(f"  ✅ Saved as hook_{index:03d}.mp4")
        except Exception as e:
            append_line(FAILED_LOG, url)
            print(f"  ❌ Failed: {e}")

    print(f"\nDone. {success_count} hooks saved to '{HOOKS_DIR}/'")
    print(f"Failures logged to: {FAILED_LOG}")


if __name__ == "__main__":
    main()
