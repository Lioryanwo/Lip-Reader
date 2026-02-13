import os
import json
import yt_dlp
import sys
import time
import random
from dotenv import load_dotenv

# -------------------------------------------------
# Project root
# -------------------------------------------------
current_script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_script_path))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.common import setup_logger, sanitize_filename

load_dotenv()

# -------------------------------------------------
# ENV CONFIG
# -------------------------------------------------
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", r"C:\VLM-Lip-Reader\data\01_raw_videos")
SOURCES_FILE = os.getenv("SOURCES_FILE", "assets/configs/source_urls.json")
COOKIES_FILE = os.getenv("COOKIES_FILE", "assets/config/youtube_cookies.txt")
LOG_FOLDER = os.getenv("LOGS_DIR", "logs")

TARGET_HEIGHT = int(os.getenv("TARGET_HEIGHT", 1080))
MIN_HEIGHT = int(os.getenv("MIN_HEIGHT", 720))
TARGET_FPS = int(os.getenv("TARGET_FPS", 25))
MIN_FPS = int(os.getenv("MIN_FPS_TO_DOWNLOAD", 20))

START_FROM = int(os.getenv("START_FROM", 1))

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)

error_logger = setup_logger('error_logger', os.path.join(LOG_FOLDER, 'download_errors.log'))
success_logger = setup_logger('success_logger', os.path.join(LOG_FOLDER, 'download_success.log'))

# -------------------------------------------------

def filter_video_quality(info, *, incomplete):
    fps = info.get('fps')
    height = info.get('height')

    if fps is not None and fps < MIN_FPS:
        return f"FPS {fps} < {MIN_FPS}"

    if height is not None and height < MIN_HEIGHT:
        return f"Height {height} < {MIN_HEIGHT}"

    return None

# -------------------------------------------------

def human_sleep():
    t = random.uniform(20, 45)
    print(f"😴 Sleeping {round(t,1)}s...")
    time.sleep(t)

# -------------------------------------------------

def file_exists_with_prefix(index_prefix):
    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith(index_prefix):
            return True
    return False

# -------------------------------------------------

def download_single_video(entry, index, total_digits):

    existing_files = os.listdir(DOWNLOAD_DIR)

    if any(sanitize_filename(entry.get("url", "")) in f for f in existing_files):
        return "⏭️ Already downloaded"

    url = entry.get("url")
    if not url:
        return "❌ Missing URL"

    speaker = sanitize_filename(entry.get("speaker_id", "unknown"))

    padded_index = str(index).zfill(total_digits)
    filename_prefix = f"{padded_index}_{speaker}"

    if file_exists_with_prefix(filename_prefix):
        return f"⏭️ Skipped (exists): {filename_prefix}"

    try:
        ydl_opts = {
            'outtmpl': os.path.join(
                DOWNLOAD_DIR,
                f"{filename_prefix}_%(title)s.%(ext)s"
            ),
            'windowsfilenames': True,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'match_filter': filter_video_quality,
            'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
            'nopart': True,
            'retries': 10,
            'rate_limit': '1M',
            'quiet': True,
            'no_warnings': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0'
            },
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4'
            }],
            'postprocessor_args': [
                '-r', str(TARGET_FPS),
                '-vf', f'scale=-2:{TARGET_HEIGHT}',
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                '-c:a', 'aac', '-b:a', '128k'
            ]
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        success_logger.info(url)
        return f"✅ Downloaded: {filename_prefix}"

    except Exception as e:
        error_logger.error(f"{url}: {e}")
        return f"❌ ERROR: {url}"

# -------------------------------------------------

def main():
    if not os.path.exists(SOURCES_FILE):
        print(f"❌ Missing config: {SOURCES_FILE}")
        return

    with open(SOURCES_FILE, encoding="utf-8") as f:
        videos = json.load(f)

    total_videos = len(videos)
    total_digits = len(str(total_videos))

    print(f"🎬 Total videos: {total_videos}")
    print(f"▶ Starting from index: {START_FROM}\n")

    for idx, video in enumerate(videos, 1):

        if idx < START_FROM:
            continue

        print(f"[{idx}/{total_videos}]")
        result = download_single_video(video, idx, total_digits)
        print(result)

        if idx < total_videos:
            human_sleep()

    print("\n✅ Finished safely.")

# -------------------------------------------------

if __name__ == "__main__":
    main()