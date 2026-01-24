# Contributing to Agent Rules Sync

Thanks for your interest in contributing! This project is open to all types of contributions.

## Development Setup

```bash
git clone https://github.com/yourusername/agent-rules-sync.git
cd agent-rules-sync

# Install in editable mode
pip install -e .

# Start testing
agent-rules-sync watch
```

## Testing Your Changes

```bash
# Watch mode in foreground (easiest for debugging)
python3 agent_rules_sync.py watch

# Check status
python3 agent_rules_sync.py status

# Manually trigger sync
python3 -c "from agent_rules_sync import AgentRulesSync; AgentRulesSync().sync()"
```

## Code Style

- Python 3.8+ compatible
- No external dependencies required (uses stdlib only)
- Keep it simple and readable
- Add comments for complex logic

## Bug Reports

Include:
- Python version (`python3 --version`)
- OS (macOS, Linux, Windows)
- Steps to reproduce
- Expected vs actual behavior

## Feature Requests

Describe:
- The use case
- Why it would be useful
- Proposed API/behavior

## Pull Request Process

1. Fork and create feature branch
2. Test your changes thoroughly
3. Update README if needed
4. Submit PR with clear description

## Questions?

Open an issue and we'll discuss!
