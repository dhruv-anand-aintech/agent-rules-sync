#!/usr/bin/env python3
"""
Method 2: Extract YouTube watch history using yt-dlp.
This script executes yt-dlp using subprocess, fetches the private YouTube history feed,
parses the output, and merges the video metadata into a local JSON database.
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime

# Default output file
OUTPUT_HISTORY_JSON = os.path.expanduser("~/youtube_watch_history.json")

# Default path to Chrome Canary profile for cookie extraction
DEFAULT_CANARY_PROFILE = os.path.expanduser(
    "~/Library/Application Support/Google/Chrome Canary/Default"
)

def run_ytdlp(browser=None, cookies_file=None, max_entries=50):
    cmd = [
        "yt-dlp",
        "--playlist-end", str(max_entries),
        "--flat-playlist",
        "--dump-single-json",
        "https://www.youtube.com/feed/history"
    ]

    if cookies_file:
        if not os.path.exists(cookies_file):
            print(f"Error: Cookies file not found at: {cookies_file}")
            sys.exit(1)
        cmd.extend(["--cookies", cookies_file])
        print(f"Using cookies file: {cookies_file}")
    elif browser:
        cmd.extend(["--cookies-from-browser", browser])
        print(f"Extracting cookies from browser: {browser}")
    else:
        # Fall back to Chrome Canary profile if present
        if os.path.exists(DEFAULT_CANARY_PROFILE):
            cookie_arg = f"chrome:{DEFAULT_CANARY_PROFILE}"
            cmd.extend(["--cookies-from-browser", cookie_arg])
            print(f"Extracting cookies from Chrome Canary Default profile...")
        else:
            print("Error: No browser profile or cookies file specified, and Chrome Canary was not found.")
            print("Use --browser <name> or --cookies <file>.")
            sys.exit(1)

    print(f"Running command: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"\nError running yt-dlp (Exit code {e.returncode}):")
        print(e.stderr)
        print("\nNote: YouTube session cookies might have expired. Please verify you are logged in.")
        print("You can also export cookies to a Netscape cookies.txt file using a browser extension")
        print("and run this script with: python ytdlp_history.py --cookies /path/to/cookies.txt")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def merge_and_save(feed_data):
    if not feed_data or "entries" not in feed_data:
        print("No entries found in YouTube history feed.")
        return

    new_items = []
    # yt-dlp returns entries in reverse chronological order (newest first)
    for entry in feed_data["entries"]:
        if not entry:
            continue
        
        video_id = entry.get("id")
        title = entry.get("title")
        url = entry.get("url") or f"https://www.youtube.com/watch?v={video_id}"
        
        # Note: feed/history does not always contain exact watch timestamps,
        # so we record the capture timestamp if not present, or use the epoch from yt-dlp metadata.
        epoch = feed_data.get("epoch")
        timestamp = datetime.utcfromtimestamp(epoch).isoformat() + "Z" if epoch else datetime.utcnow().isoformat() + "Z"

        if video_id:
            new_items.append({
                "video_id": video_id,
                "title": title,
                "url": url,
                "timestamp": timestamp,
                "duration_sec": entry.get("duration"),
                "channel": entry.get("channel") or entry.get("uploader"),
                "channel_id": entry.get("channel_id") or entry.get("uploader_id"),
                "source": "ytdlp_history_feed"
            })

    existing_items = {}
    if os.path.exists(OUTPUT_HISTORY_JSON):
        try:
            with open(OUTPUT_HISTORY_JSON, "r") as f:
                data = json.load(f)
                for item in data:
                    # Identify uniqueness by video_id
                    existing_items[item["video_id"]] = item
        except Exception as e:
            print(f"Error loading existing history: {e}")

    # Merge new items. Since yt-dlp works on video list, we overwrite/update existing items with newer metadata.
    added_count = 0
    for item in new_items:
        if item["video_id"] not in existing_items:
            existing_items[item["video_id"]] = item
            added_count += 1
        else:
            # Update existing metadata (like title, channel, duration) but keep the original watch timestamp if possible
            orig_ts = existing_items[item["video_id"]].get("timestamp")
            existing_items[item["video_id"]].update(item)
            if orig_ts:
                existing_items[item["video_id"]]["timestamp"] = orig_ts

    sorted_history = sorted(existing_items.values(), key=lambda x: x.get("timestamp", ""))

    with open(OUTPUT_HISTORY_JSON, "w") as f:
        json.dump(sorted_history, f, indent=2)

    print(f"Successfully processed YouTube history feed.")
    print(f"Added {added_count} new unique videos. Total unique videos tracked: {len(sorted_history)}")
    print(f"History saved to: {OUTPUT_HISTORY_JSON}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dump YouTube watch history using yt-dlp")
    parser.add_argument("--browser", help="Browser to extract cookies from (e.g. safari, firefox, chrome)")
    parser.add_argument("--cookies", help="Path to Netscape cookies.txt file")
    parser.add_argument("--max", type=int, default=50, help="Maximum history entries to fetch (default: 50)")
    args = parser.parse_args()

    feed = run_ytdlp(browser=args.browser, cookies_file=args.cookies, max_entries=args.max)
    if feed:
        merge_and_save(feed)
