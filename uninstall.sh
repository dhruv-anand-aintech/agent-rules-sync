#!/bin/bash
# Agent Rules Sync - Uninstall Script
# Works on macOS, Linux, and Windows (with bash/WSL)

set -e

echo "🗑️  Uninstalling Agent Rules Sync..."

# Detect platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "Unloading macOS launchd service..."
    PLIST="$HOME/Library/LaunchAgents/com.local.agent-rules-sync.plist"
    if [ -f "$PLIST" ]; then
        launchctl unload "$PLIST" 2>/dev/null || true
        rm -f "$PLIST"
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    echo "Stopping systemd service..."
    systemctl --user stop agent-rules-sync.service 2>/dev/null || true
    systemctl --user disable agent-rules-sync.service 2>/dev/null || true
    systemctl --user daemon-reload 2>/dev/null || true
    rm -f ~/.config/systemd/user/agent-rules-sync.service 2>/dev/null || true
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    echo "Removing Windows startup batch file..."
    rm -f "$APPDATA/Microsoft/Windows/Start Menu/Programs/Startup/agent-rules-sync.bat" 2>/dev/null || true
fi

# Stop daemon if running
echo "Stopping daemon..."
agent-rules-sync stop 2>/dev/null || true

# Kill any remaining agent-rules-sync processes
pkill -f "agent-rules-sync" 2>/dev/null || true
sleep 1

# Uninstall package
echo "Removing pip package..."
pip uninstall -y agent-rules-sync 2>/dev/null || python3 -m pip uninstall -y agent-rules-sync 2>/dev/null || true

# Clean up config directory
echo "Removing config directory..."
rm -rf ~/.config/agent-rules-sync

echo ""
echo "✓ Agent Rules Sync uninstalled successfully"
echo ""
echo "Your agent rule files are preserved at:"
echo "  ~/.claude/CLAUDE.md"
echo "  ~/.cursor/rules/global.mdc"
echo "  ~/.gemini/GEMINI.md"
echo "  ~/.config/opencode/AGENTS.md"
