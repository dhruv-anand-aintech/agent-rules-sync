#!/usr/bin/env python3
"""
Method 3: Local FastAPI webhook listener for YouTube watch events.
This server runs on localhost and receives POST requests from a Tampermonkey userscript.
"""

import os
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="YouTube History Sync Server")

# Enable CORS so the Tampermonkey userscript running on youtube.com can POST to localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict this to ["https://www.youtube.com"] if desired
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# Output JSON file path
OUTPUT_HISTORY_JSON = os.path.expanduser("~/youtube_watch_history.json")

class HistoryEvent(BaseModel):
    video_id: str
    title: str
    url: str
    channel: str
    timestamp: str = None  # Will default to current time if not provided

@app.post("/history")
async def receive_history_event(event: HistoryEvent):
    # Set timestamp if not provided
    event_timestamp = event.timestamp or datetime.utcnow().isoformat() + "Z"
    
    new_entry = {
        "video_id": event.video_id,
        "title": event.title,
        "url": event.url,
        "timestamp": event_timestamp,
        "channel": event.channel,
        "source": "tampermonkey_userscript"
    }

    # Load existing history
    existing_items = {}
    if os.path.exists(OUTPUT_HISTORY_JSON):
        try:
            with open(OUTPUT_HISTORY_JSON, "r") as f:
                data = json.load(f)
                for item in data:
                    key = (item["video_id"], item.get("timestamp", ""))
                    existing_items[key] = item
        except Exception as e:
            print(f"Error loading existing history: {e}")

    # Add new entry
    key = (new_entry["video_id"], new_entry["timestamp"])
    
    # Simple rate-limiting/deduping: don't log the same video if watched in the same minute
    # (Sometimes userscripts trigger multiple loads of the same page)
    already_exists = False
    for k, existing in existing_items.items():
        if existing["video_id"] == new_entry["video_id"]:
            # If the video was watched in the last 2 minutes, ignore duplicate event
            try:
                t1 = datetime.fromisoformat(existing["timestamp"].replace("Z", ""))
                t2 = datetime.fromisoformat(new_entry["timestamp"].replace("Z", ""))
                if abs((t1 - t2).total_seconds()) < 120:
                    already_exists = True
                    break
            except Exception:
                pass

    if not already_exists:
        existing_items[key] = new_entry
        sorted_history = sorted(existing_items.values(), key=lambda x: x.get("timestamp", ""))

        try:
            with open(OUTPUT_HISTORY_JSON, "w") as f:
                json.dump(sorted_history, f, indent=2)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Logged video: {event.title} by {event.channel}")
            return {"status": "success", "message": "Video logged successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to write history file: {e}")
    
    return {"status": "ignored", "message": "Duplicate event ignored"}

if __name__ == "__main__":
    import uvicorn
    print(f"Starting local sync server on http://localhost:8000")
    print(f"Writing history to: {OUTPUT_HISTORY_JSON}")
    uvicorn.run(app, host="127.0.0.1", port=8000)
