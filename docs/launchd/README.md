# Launchd Setup (Generalized)

This folder contains a reusable, non-user-specific launchd setup for the
`agent-rules-sync` daemon and the 5GiB hard disk guard.

- `com.local.agent-rules-sync.plist.template`: launchd plist with placeholders
- `run-watch-foreground.example.py`: launchd entry script that enables disk checks

## 1) Prepare the foreground runner

```bash
mkdir -p ~/.config/agent-rules-sync
cp docs/launchd/run-watch-foreground.example.py \
  ~/.config/agent-rules-sync/run-watch-foreground.py
chmod +x ~/.config/agent-rules-sync/run-watch-foreground.py
```

If your repo is not at `~/Code/agent-rules-sync-standalone`, edit
`AGENT_RULES_SYNC_REPO` in your environment or keep the default path resolution by
running the script from within your repo.

## 2) Generate and install LaunchAgent plist

Create `~/Library/LaunchAgents/com.local.agent-rules-sync.plist` from the template,
replacing placeholders:

- `{{LAUNCHD_LABEL}}` (default: `com.local.agent-rules-sync`)
- `{{PYTHON_BIN}}` (for example `/usr/bin/python3` or your Conda/venv `python3`)
- `{{RUN_WATCH_SCRIPT}}` (for example `~/.config/agent-rules-sync/run-watch-foreground.py`)
- `{{REPO_ROOT}}` (repo checkout path, for example `/Users/you/Code/agent-rules-sync-standalone`)
- `{{STDOUT_LOG}}` / `{{STDERR_LOG}}` (for example `~/.config/agent-rules-sync/stdout.log` and `~/.config/agent-rules-sync/stderr.log`)
- `{{DISK_LIMIT_BYTES}}` (default is `5368709120` = 5GiB)
- `{{PATH_VALUE}}` (your normal PATH as a single string)

```bash
cp docs/launchd/com.local.agent-rules-sync.plist.template \
  ~/Library/LaunchAgents/com.local.agent-rules-sync.plist
```

Open the file and replace placeholders, then load it:

```bash
launchctl load ~/Library/LaunchAgents/com.local.agent-rules-sync.plist
```

## 3) Verify

```bash
launchctl print gui/$(id -u)/com.local.agent-rules-sync
launchctl print gui/$(id -u) | rg -n "com.local.agent-rules-sync"
```

To stop and unload:

```bash
launchctl unload ~/Library/LaunchAgents/com.local.agent-rules-sync.plist
```
