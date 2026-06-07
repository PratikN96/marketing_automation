import os

# ── YouTube channel to scrape hooks from ──────────────────────────────────────
HOOK_CHANNEL_URL = "https://www.youtube.com/@ZackDFilms/shorts"  # change this
HOOKS_COUNT = 25  # how many hooks to scrape (a few extra as buffer)
HOOKS_DIR = "hooks"

# ── CTA video ─────────────────────────────────────────────────────────────────
CTA_VIDEO_PATH = "cta.mp4"  # place your CTA clip here

# ── Output ────────────────────────────────────────────────────────────────────
FINAL_DIR = "final"

# ── YouTube upload schedule ───────────────────────────────────────────────────
VIDEOS_PER_DAY = 3
# Times (UTC) to publish each day — 3 slots
PUBLISH_TIMES_UTC = ["13:00", "17:00", "21:00"]  # 9am, 1pm, 5pm EST

# ── YouTube API (set via env vars or GitHub Secrets) ─────────────────────────
YOUTUBE_CLIENT_ID     = os.environ.get("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")

# ── GitHub (for release asset uploads) ───────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO  = os.environ.get("GITHUB_REPO", "")  # e.g. "youruser/marketing_automation"

# ── YouTube channel ───────────────────────────────────────────────────────────
YOUTUBE_CHANNEL_HANDLE = "@JesusIsKing-thelord"

# ── Video metadata ────────────────────────────────────────────────────────────
VIDEO_TITLE_PREFIX  = ""
VIDEO_DESCRIPTION   = ""
VIDEO_TAGS          = ["jesus", "christian", "faith", "shorts", "viral"]
VIDEO_CATEGORY_ID   = "29"   # 29 = Nonprofits & Activism
