#!/bin/bash
# Agent Rules Sync - Uninstall Script
# Works on macOS, Linux, and Windows (with bash/WSL)

set -e

echo "🗑️  Uninstalling Agent Rules Sync..."

# Stop daemon if running
echo "Stopping daemon..."
agent-rules-sync stop 2>/dev/null || true

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
