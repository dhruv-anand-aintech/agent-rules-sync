#!/usr/bin/env python3
"""
Method 1: Extract YouTube watch history from all local browsers on macOS.
Scans for Chrome, Chrome Canary, Edge, Edge Dev, Arc, Brave, Firefox, and Safari,
copies their SQLite databases, queries for YouTube watch URLs, converts their respective
timestamps, and merges them into a consolidated local JSON history file.
"""

import os
import shutil
import sqlite3
import json
import glob
from datetime import datetime

# Consolidated JSON history output file
OUTPUT_HISTORY_JSON = os.path.expanduser("~/youtube_watch_history.json")
TEMP_DB_PATH = os.path.expanduser("~/youtube_history_db_temp")

# Define search patterns for browser history paths on macOS
BROWSER_PATHS = {
    "Google Chrome": {
        "type": "chromium",
        "patterns": [
            "~/Library/Application Support/Google/Chrome/Default/History",
            "~/Library/Application Support/Google/Chrome/Profile */History"
        ]
    },
    "Google Chrome Canary": {
        "type": "chromium",
        "patterns": [
            "~/Library/Application Support/Google/Chrome Canary/Default/History",
            "~/Library/Application Support/Google/Chrome Canary/Profile */History"
        ]
    },
    "Microsoft Edge": {
        "type": "chromium",
        "patterns": [
            "~/Library/Application Support/Microsoft Edge/Default/History",
            "~/Library/Application Support/Microsoft Edge/Profile */History"
        ]
    },
    "Microsoft Edge Dev": {
        "type": "chromium",
        "patterns": [
            "~/Library/Application Support/Microsoft Edge Dev/Default/History",
            "~/Library/Application Support/Microsoft Edge Dev/Profile */History"
        ]
    },
    "Brave": {
        "type": "chromium",
        "patterns": [
            "~/Library/Application Support/BraveSoftware/Brave-Browser/Default/History",
            "~/Library/Application Support/BraveSoftware/Brave-Browser/Profile */History"
        ]
    },
    "Arc": {
        "type": "chromium",
        "patterns": [
            "~/Library/Application Support/Arc/User Data/Default/History",
            "~/Library/Application Support/Arc/User Data/Profile */History"
        ]
    },
    "Firefox": {
        "type": "firefox",
        "patterns": [
            "~/Library/Application Support/Firefox/Profiles/*/places.sqlite"
        ]
    },
    "Safari": {
        "type": "safari",
        "patterns": [
            "~/Library/Safari/History.db"
        ]
    }
}

def clean_title(title):
    if not title:
        return "Unknown Title"
    if title.endswith(" - YouTube"):
        return title[:-10]
    return title

def parse_chromium_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
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
    
    items = []
    for url, title, webkit_time, duration in rows:
        # Convert WebKit epoch (microseconds since 1601-01-01) to Unix timestamp
        unix_time = (webkit_time / 1000000.0) - 11644473600.0
        visit_dt = datetime.utcfromtimestamp(unix_time)
        video_id = None
        if "v=" in url:
            video_id = url.split("v=")[1].split("&")[0]

        if video_id:
            items.append({
                "video_id": video_id,
                "title": clean_title(title),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "timestamp": visit_dt.isoformat() + "Z",
                "duration_sec": duration / 1000000.0,
                "source": "chromium_history"
            })
    conn.close()
    return items

def parse_firefox_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = """
    SELECT p.url, p.title, v.visit_date
    FROM moz_places p
    JOIN moz_historyvisits v ON p.id = v.place_id
    WHERE p.url LIKE '%youtube.com/watch%'
    ORDER BY v.visit_date DESC
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    items = []
    for url, title, visit_date in rows:
        # Convert Firefox epoch (microseconds since Unix epoch 1970-01-01)
        visit_dt = datetime.utcfromtimestamp(visit_date / 1000000.0)
        video_id = None
        if "v=" in url:
            video_id = url.split("v=")[1].split("&")[0]

        if video_id:
            items.append({
                "video_id": video_id,
                "title": clean_title(title),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "timestamp": visit_dt.isoformat() + "Z",
                "duration_sec": 0.0,
                "source": "firefox_history"
            })
    conn.close()
    return items

def parse_safari_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = """
    SELECT i.url, v.title, v.visit_time
    FROM history_items i
    JOIN history_visits v ON i.id = v.history_item
    WHERE i.url LIKE '%youtube.com/watch%'
    ORDER BY v.visit_time DESC
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    items = []
    for url, title, visit_time in rows:
        # Convert Safari epoch (seconds since 2001-01-01) to Unix timestamp
        unix_time = visit_time + 978307200.0
        visit_dt = datetime.utcfromtimestamp(unix_time)
        video_id = None
        if "v=" in url:
            video_id = url.split("v=")[1].split("&")[0]

        if video_id:
            items.append({
                "video_id": video_id,
                "title": clean_title(title),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "timestamp": visit_dt.isoformat() + "Z",
                "duration_sec": 0.0,
                "source": "safari_history"
            })
    conn.close()
    return items

def get_browser_history():
    all_items = []
    
    for browser_name, info in BROWSER_PATHS.items():
        type_ = info["type"]
        found_files = []
        for pattern in info["patterns"]:
            expanded = os.path.expanduser(pattern)
            found_files.extend(glob.glob(expanded))

        if not found_files:
            continue

        print(f"Scanning {browser_name} ({len(found_files)} profile(s) found)...")
        for db_path in found_files:
            if not os.path.exists(db_path):
                continue
            
            try:
                # Copy to temporary path to bypass file locks if browser is open
                shutil.copy2(db_path, TEMP_DB_PATH)
                
                if type_ == "chromium":
                    items = parse_chromium_db(TEMP_DB_PATH)
                elif type_ == "firefox":
                    items = parse_firefox_db(TEMP_DB_PATH)
                elif type_ == "safari":
                    items = parse_safari_db(TEMP_DB_PATH)
                
                # Tag items with specific browser source
                for item in items:
                    item["source"] = f"{browser_name.lower().replace(' ', '_')}_history"
                
                all_items.extend(items)
                print(f"  -> Extracted {len(items)} events from: {db_path}")
            except sqlite3.OperationalError as e:
                if "encrypted" in str(e).lower() or "permission" in str(e).lower():
                    print(f"  -> Skipping {browser_name} (Database locked, encrypted, or lacks Full Disk Access permissions).")
                else:
                    print(f"  -> Error reading database {db_path}: {e}")
            except Exception as e:
                print(f"  -> Error processing {db_path}: {e}")
            finally:
                if os.path.exists(TEMP_DB_PATH):
                    os.remove(TEMP_DB_PATH)
                    
    return all_items

def merge_and_save(new_items):
    existing_items = {}
    if os.path.exists(OUTPUT_HISTORY_JSON):
        try:
            with open(OUTPUT_HISTORY_JSON, "r") as f:
                data = json.load(f)
                for item in data:
                    key = (item["video_id"], item.get("timestamp", ""))
                    existing_items[key] = item
        except Exception as e:
            print(f"Error loading existing history file: {e}")

    added_count = 0
    for item in new_items:
        key = (item["video_id"], item["timestamp"])
        if key not in existing_items:
            existing_items[key] = item
            added_count += 1

    # Sort history chronologically (oldest first, latest last)
    sorted_history = sorted(existing_items.values(), key=lambda x: x["timestamp"])

    with open(OUTPUT_HISTORY_JSON, "w") as f:
        json.dump(sorted_history, f, indent=2)

    print(f"\nMerged {added_count} new watch events. Total history records in database: {len(sorted_history)}")
    print(f"Database saved to: {OUTPUT_HISTORY_JSON}")

if __name__ == "__main__":
    print("Starting Multi-Browser YouTube watch history dump...")
    items = get_browser_history()
    print(f"Total watch events retrieved across all browsers: {len(items)}")
    if items:
        merge_and_save(items)
