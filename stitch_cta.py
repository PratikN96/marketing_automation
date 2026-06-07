"""
Step 2: Stitch CTA video to the end of every hook.
Re-encodes both to the same format before concatenating.

Usage:
    python stitch_cta.py --hooks hooks/ --cta cta.mp4 --output final/
"""

import argparse
import os
import subprocess
import sys
import tempfile


SUCCESS_LOG = "stitch_success.txt"
FAILURE_LOG = "stitch_failed.txt"


def load_set(filepath):
    if not os.path.exists(filepath):
        return set()
    with open(filepath) as f:
        return set(line.strip() for line in f if line.strip())


def append_line(filepath, line):
    with open(filepath, "a") as f:
        f.write(line + "\n")


def normalize_clip(input_path, output_path):
    """Re-encode a clip to standard format: 1080x1920, h264, aac 44100."""
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
        "-c:a", "aac", "-ar", "44100", "-ac", "2",
        "-r", "30",
        "-movflags", "+faststart",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode())


def concat_clips(clip1, clip2, output_path):
    """Concatenate two pre-normalized clips using ffmpeg concat demuxer."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(f"file '{os.path.abspath(clip1)}'\n")
        f.write(f"file '{os.path.abspath(clip2)}'\n")
        concat_file = f.name

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True)
    os.unlink(concat_file)

    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode())


def main():
    parser = argparse.ArgumentParser(description="Stitch CTA to hook videos")
    parser.add_argument("--hooks", required=True, help="Folder containing hook videos")
    parser.add_argument("--cta", required=True, help="Path to CTA video")
    parser.add_argument("--output", required=True, help="Output folder for final videos")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing final videos")
    parser.add_argument("--limit", type=int, default=None, help="Max number of videos to stitch")
    args = parser.parse_args()

    if not os.path.exists(args.hooks):
        print(f"❌ Hooks folder not found: {args.hooks}")
        sys.exit(1)

    if not os.path.exists(args.cta):
        print(f"❌ CTA video not found: {args.cta}")
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)

    hooks = sorted([
        f for f in os.listdir(args.hooks)
        if f.endswith(".mp4")
    ])

    if not hooks:
        print(f"❌ No .mp4 files found in {args.hooks}")
        sys.exit(1)

    if args.limit:
        hooks = hooks[:args.limit]

    print(f"Found {len(hooks)} hooks. Normalizing CTA clip once...")

    already_done = load_set(SUCCESS_LOG)

    # Normalize CTA once and reuse
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        normalized_cta = f.name

    try:
        normalize_clip(args.cta, normalized_cta)
        print(f"✅ CTA normalized.\n")

        success_count = 0
        for i, hook_file in enumerate(hooks, start=1):
            hook_path = os.path.join(args.hooks, hook_file)
            index = int(hook_file.replace("hook_", "").replace(".mp4", ""))
            output_path = os.path.join(args.output, f"final_{index:03d}.mp4")

            if hook_path in already_done and not args.overwrite:
                print(f"Skipping {i}/{len(hooks)} (already stitched): {hook_file}")
                continue

            if os.path.exists(output_path) and not args.overwrite:
                print(f"Skipping {i}/{len(hooks)} (output exists): final_{index:03d}.mp4")
                continue

            print(f"Processing {i}/{len(hooks)}: {hook_file}")

            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                normalized_hook = f.name

            try:
                normalize_clip(hook_path, normalized_hook)
                concat_clips(normalized_hook, normalized_cta, output_path)
                append_line(SUCCESS_LOG, hook_path)
                success_count += 1
                print(f"  ✅ Saved as final_{index:03d}.mp4")
            except Exception as e:
                append_line(FAILURE_LOG, hook_path)
                print(f"  ❌ Failed: {e}")
            finally:
                if os.path.exists(normalized_hook):
                    os.unlink(normalized_hook)

    finally:
        if os.path.exists(normalized_cta):
            os.unlink(normalized_cta)

    print(f"\nDone. {success_count} final videos saved to '{args.output}/'")
    print(f"Failures logged to: {FAILURE_LOG}")


if __name__ == "__main__":
    main()
