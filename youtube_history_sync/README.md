# YouTube Watch History Sync Suite

A suite of tools to automate dumping your YouTube watch history locally on macOS.

## Setup & Options

Choose one of the three methods below. All methods output history to a single consolidated file: `~/youtube_watch_history.json`.

---

### Method 1: Multi-Browser SQLite Reader (Recommended, Fully Local & Automated)
Extracts history from local databases of all installed browsers (Chrome, Chrome Canary, Edge, Edge Dev, Arc, Brave, Firefox, Safari). It includes entries synced from other devices if browser history sync is active.

**Prerequisites:** None (uses built-in Python libraries).
**Run once:**
```bash
python3 youtube_history_sync/browser_history.py
```

---

### Method 2: Cookie-based `yt-dlp` Sync (Complete Account History)
Uses `yt-dlp` (already installed on your machine) to fetch your private history feed. Requires a valid session from your browser or an exported cookie file.

**Prerequisites:** `yt-dlp` (already installed on your machine).
**Run once (attempts to extract cookies from Chrome Canary):**
```bash
python3 youtube_history_sync/ytdlp_history.py
```
*Note: If your browser cookies rotate or expire, you can export them to a file (using a browser extension like "Get cookies.txt LOCALLY") and run:*
```bash
python3 youtube_history_sync/ytdlp_history.py --cookies ~/Downloads/cookies.txt
```

---

### Method 3: Real-Time Sync (FastAPI Webhook Server + Tampermonkey Userscript)
Captures watches in real-time as you view them on your desktop. It posts events from your browser to a local background service.

**Prerequisites:** `fastapi` and `uvicorn` (run automatically with `uv`).
**Start the local receiver server:**
```bash
uv run --with fastapi,uvicorn,pydantic youtube_history_sync/webhook_history.py
```
**Browser Setup:**
1. Install the **Tampermonkey** extension in your browser.
2. Create a new script, copy the contents of `youtube_history_sync/youtube_tracker.user.js` into it, and save.
3. Keep the FastAPI server running. Any video you watch on YouTube will be logged instantly.

---

## Scheduling Nightly Runs (Methods 1 & 2)

To run **Method 1** or **Method 2** automatically every night at 11:30 PM, use macOS's native service manager, `launchd`.

1. Copy the plist file to your LaunchAgents directory:
   ```bash
   cp youtube_history_sync/com.youtube.history.sync.plist ~/Library/LaunchAgents/
   ```
2. Open `~/Library/LaunchAgents/com.youtube.history.sync.plist` in an editor and check:
   - Ensure the Python path (`/Users/dhruvanand/miniforge3/bin/python3`) is correct.
   - Update the script path (`/Users/dhruvanand/Code/agent-rules-sync-standalone/youtube_history_sync/browser_history.py` or `ytdlp_history.py`) to match where your repo is located.
3. Load the agent to activate it:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.youtube.history.sync.plist
   ```
4. Verify or test launch it manually right now:
   ```bash
   launchctl start com.youtube.history.sync
   ```
   Logs will be written to `~/youtube_history_sync_out.log` and `~/youtube_history_sync_err.log`.
