#!/usr/bin/env python3
"""
Method 1: Extract YouTube watch history from local Chrome Canary SQLite database.
This script copies the Chrome Canary History database, queries for YouTube video
watch events, dedupes them, and merges them into a local JSON history file.
"""

import os
import shutil
import sqlite3
import json
from datetime import datetime, timedelta

# Path to Google Chrome Canary History SQLite database on macOS
CHROME_CANARY_HISTORY = os.path.expanduser(
    "~/Library/Application Support/Google/Chrome Canary/Default/History"
)
# Output JSON file to store your aggregated history
OUTPUT_HISTORY_JSON = os.path.expanduser("~/youtube_watch_history.json")
# Temporary database copy path to prevent SQLite database lock issues
TEMP_DB_PATH = os.path.expanduser("~/youtube_history_db_temp")

def get_youtube_history():
    if not os.path.exists(CHROME_CANARY_HISTORY):
        print(f"Error: Chrome Canary History database not found at: {CHROME_CANARY_HISTORY}")
        return []

    # Copy the database file to avoid locking issues while Chrome is running
    print(f"Copying Chrome Canary History database...")
    shutil.copy2(CHROME_CANARY_HISTORY, TEMP_DB_PATH)

    try:
        conn = sqlite3.connect(TEMP_DB_PATH)
        cursor = conn.cursor()

        # Query to fetch all YouTube watch URLs and their visit times
        # Webkit epoch starts on Jan 1, 1601. Convert to Unix timestamp by subtracting difference.
        # visit_time / 1000000 - 11644473600
        query = """
        SELECT 
            urls.url, 
            urls.title, 
            visits.visit_time,
            visits.visit_duration
        FROM urls
        JOIN visits ON urls.id = visits.url
        WHERE urls.url LIKE '%youtube.com/watch%'
        ORDER BY visits.visit_time DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        history_items = []
        for url, title, webkit_time, duration in rows:
            # Convert webkit timestamp to standard ISO datetime string
            unix_time = (webkit_time / 1000000.0) - 11644473600.0
            visit_dt = datetime.utcfromtimestamp(unix_time)
            
            # Clean up YouTube titles (e.g. remove " - YouTube")
            clean_title = title
            if title.endswith(" - YouTube"):
                clean_title = title[:-10]

            # Extract video ID from URL
            video_id = None
            if "v=" in url:
                video_id = url.split("v=")[1].split("&")[0]

            if video_id:
                history_items.append({
                    "video_id": video_id,
                    "title": clean_title,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "timestamp": visit_dt.isoformat() + "Z",
                    "duration_sec": duration / 1000000.0,  # microseconds to seconds
                    "source": "chrome_canary_history"
                })
        
        return history_items
    except Exception as e:
        print(f"Error reading SQLite database: {e}")
        return []
    finally:
        # Clean up temporary database copy
        if os.path.exists(TEMP_DB_PATH):
            os.remove(TEMP_DB_PATH)

def merge_and_save(new_items):
    existing_items = {}
    if os.path.exists(OUTPUT_HISTORY_JSON):
        try:
            with open(OUTPUT_HISTORY_JSON, "r") as f:
                data = json.load(f)
                # Group by video_id and timestamp to avoid duplicates
                for item in data:
                    key = (item["video_id"], item.get("timestamp", ""))
                    existing_items[key] = item
        except Exception as e:
            print(f"Error loading existing history: {e}")

    # Add new items if they aren't already saved
    added_count = 0
    for item in new_items:
        key = (item["video_id"], item["timestamp"])
        if key not in existing_items:
            existing_items[key] = item
            added_count += 1

    # Sort history chronologically (latest visits last or first, let's keep latest last)
    sorted_history = sorted(existing_items.values(), key=lambda x: x["timestamp"])

    with open(OUTPUT_HISTORY_JSON, "w") as f:
        json.dump(sorted_history, f, indent=2)

    print(f"Merged {added_count} new watch events. Total history records: {len(sorted_history)}")
    print(f"History saved to: {OUTPUT_HISTORY_JSON}")

if __name__ == "__main__":
    print(f"Starting Chrome Canary watch history dump...")
    items = get_youtube_history()
    print(f"Found {len(items)} YouTube watch events in browser history.")
    if items:
        merge_and_save(items)
