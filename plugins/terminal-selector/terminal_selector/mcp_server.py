from typing import Any
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp.server.fastmcp import FastMCP

from terminal_selector.selector import normalize_options, run_selector

mcp = FastMCP(
    "terminal-selector",
    instructions=(
        "Terminal-native selector tools. These tools attempt to open /dev/tty for "
        "interactive selection so MCP stdio remains reserved for JSON-RPC."
    ),
)


def _select(mode: str, title: str, options: list[Any]) -> dict[str, Any]:
    normalized = normalize_options(options)
    try:
        return run_selector(normalized, mode=mode, title=title, tty_path="/dev/tty")
    except OSError as exc:
        return {
            "mode": mode,
            "selected": [],
            "ordered": [],
            "cancelled": True,
            "error": (
                f"Could not open /dev/tty for terminal selection: {exc}. "
                "Run bin/terminal-selector directly from an interactive shell, "
                "or configure the MCP host to launch this server with a controlling terminal."
            ),
        }


@mcp.tool()
def terminal_select(title: str, options: list[Any]) -> dict[str, Any]:
    """Present a terminal-native single-choice selector and return the selected option id."""
    return _select("single", title, options)


@mcp.tool()
def terminal_multi_select(title: str, options: list[Any]) -> dict[str, Any]:
    """Present a terminal-native multi-select UI and return selected option ids."""
    return _select("multi", title, options)


@mcp.tool()
def terminal_rank(title: str, options: list[Any]) -> dict[str, Any]:
    """Present a terminal-native ranking UI and return option ids in the chosen order."""
    return _select("rank", title, options)


if __name__ == "__main__":
    mcp.run()
