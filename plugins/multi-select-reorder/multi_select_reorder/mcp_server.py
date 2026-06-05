from typing import Any
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import platform
import subprocess
import sys
import threading
import webbrowser

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp.server.fastmcp import FastMCP

from multi_select_reorder.selector import normalize_options, run_selector

mcp = FastMCP(
    "multi-select-reorder",
    instructions=(
        "Multi-select reorder tool. This opens a short-lived local web page "
        "for checkbox selection and drag-and-drop reordering."
    ),
)


def _select(
    title: str,
    options: list[Any],
    initial_selected: list[Any] | None = None,
    edit_descriptions: bool = False,
) -> dict[str, Any]:
    normalized = normalize_options(options, initial_selected=initial_selected)
    if os.environ.get("MULTI_SELECT_REORDER_DIRECT_TTY") != "1":
        return _select_in_browser(title, normalized, edit_descriptions=edit_descriptions)

    try:
        result = run_selector(normalized, mode="multi", title=title, tty_path="/dev/tty")
        result["mode"] = "multi_select_reorder"
        result["ordered"] = result.get("selected", [])
        return result
    except OSError as exc:
        return {
            "mode": "multi_select_reorder",
            "selected": [],
            "ordered": [],
            "cancelled": True,
            "error": (
                f"Could not open /dev/tty for terminal selection: {exc}. "
                "Run bin/multi-select-reorder directly from an interactive shell, "
                "or configure the MCP host to launch this server with a controlling terminal."
            ),
        }


def _select_in_browser(title: str, options: list[Any], *, edit_descriptions: bool = False) -> dict[str, Any]:
    state: dict[str, Any] = {"result": None}
    done = threading.Event()
    page = _selector_page(
        title=title,
        edit_descriptions=edit_descriptions,
        options=[
            {
                "id": option.id,
                "label": option.label,
                "description": option.description,
                "selected": option.selected,
            }
            for option in options
        ],
    )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            if self.path not in {"/", "/index.html"}:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = page.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            if self.path != "/submit":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            length = int(self.headers.get("Content-Length") or "0")
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
            state["result"] = _coerce_browser_result(options, payload)
            done.set()
            body = b'{"ok":true}'
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/"
    try:
        _open_browser(url)
        if not done.wait(3600):
            return _error_result("Web selector timed out after 1 hour")
        result = state.get("result")
        if isinstance(result, dict):
            return result
        return _error_result("Web selector returned no result")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


def _open_browser(url: str) -> None:
    if platform.system() == "Darwin":
        subprocess.run(["open", url], check=False)
    else:
        webbrowser.open(url)


def _coerce_browser_result(options: list[Any], payload: dict[str, Any]) -> dict[str, Any]:
    valid_ids = {option.id for option in options}
    selected = [str(item) for item in payload.get("selected", []) if str(item) in valid_ids]
    ordered = [str(item) for item in payload.get("ordered", []) if str(item) in valid_ids]
    selected_set = set(selected)
    ordered = [item for item in ordered if item in selected_set]
    raw_descriptions = payload.get("descriptions", {})
    descriptions = {
        str(key): str(value)
        for key, value in raw_descriptions.items()
        if str(key) in valid_ids
    } if isinstance(raw_descriptions, dict) else {}
    return {
        "mode": "multi_select_reorder",
        "selected": selected,
        "ordered": ordered,
        "descriptions": descriptions,
        "cancelled": bool(payload.get("cancelled", False)),
    }


def _selector_page(title: str, options: list[dict[str, str]], *, edit_descriptions: bool = False) -> str:
    data = json.dumps({"title": title, "options": options, "editDescriptions": edit_descriptions}, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html_escape(title)}</title>
<style>
:root {{ color-scheme: light dark; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
body {{ margin: 0; background: Canvas; color: CanvasText; }}
main {{ max-width: 760px; margin: 32px auto; padding: 0 20px 28px; }}
h1 {{ font-size: 24px; margin: 0 0 8px; }}
.hint {{ color: color-mix(in srgb, CanvasText 68%, Canvas); margin: 0 0 18px; }}
.list {{ border: 1px solid color-mix(in srgb, CanvasText 18%, Canvas); border-radius: 8px; overflow: hidden; }}
.option {{ display: grid; grid-template-columns: auto 1fr auto; gap: 12px; align-items: center; padding: 12px 14px; border-bottom: 1px solid color-mix(in srgb, CanvasText 12%, Canvas); background: Canvas; }}
.option:last-child {{ border-bottom: 0; }}
.option[draggable="true"] {{ cursor: grab; }}
.option.dragging {{ opacity: .45; }}
.option.selected {{ background: color-mix(in srgb, Highlight 15%, Canvas); }}
.label {{ font-weight: 600; }}
.description {{ font-size: 13px; color: color-mix(in srgb, CanvasText 62%, Canvas); margin-top: 3px; }}
textarea.description {{ box-sizing: border-box; width: 100%; min-height: 42px; resize: vertical; border: 1px solid color-mix(in srgb, CanvasText 18%, Canvas); border-radius: 6px; background: Canvas; color: CanvasText; padding: 6px 8px; font: inherit; font-size: 13px; }}
.rank {{ min-width: 28px; color: color-mix(in srgb, CanvasText 60%, Canvas); font-variant-numeric: tabular-nums; }}
input[type="checkbox"], input[type="radio"] {{ width: 18px; height: 18px; }}
.drag {{ font-size: 18px; color: color-mix(in srgb, CanvasText 46%, Canvas); user-select: none; }}
footer {{ display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px; }}
button {{ appearance: none; border: 1px solid color-mix(in srgb, CanvasText 20%, Canvas); border-radius: 7px; background: Canvas; color: CanvasText; padding: 9px 14px; font: inherit; cursor: pointer; }}
button.primary {{ background: Highlight; border-color: Highlight; color: HighlightText; }}
</style>
</head>
<body>
<main>
<h1 id="title"></h1>
<p id="hint" class="hint"></p>
<section id="list" class="list"></section>
<footer>
<button id="cancel" type="button">Cancel</button>
<button id="submit" class="primary" type="button">Submit</button>
</footer>
</main>
<script>
const DATA = {data};
let selected = new Set(DATA.options.filter(option => option.selected).map(option => option.id));
let ordered = DATA.options.map(option => option.id);
let dragId = null;
const titleEl = document.getElementById("title");
const hintEl = document.getElementById("hint");
const listEl = document.getElementById("list");
const submitEl = document.getElementById("submit");
const cancelEl = document.getElementById("cancel");

titleEl.textContent = DATA.title;
hintEl.textContent = "Choose one or more options. Drag rows to reorder before submitting.";

function render() {{
  listEl.innerHTML = "";
  const rows = ordered.map(id => DATA.options.find(option => option.id === id)).filter(Boolean);
  rows.forEach((option, index) => {{
    const row = document.createElement("div");
    row.className = "option" + (selected.has(option.id) ? " selected" : "");
    row.draggable = true;
    row.dataset.id = option.id;
    row.innerHTML = `
      ${{controlHtml(option, index)}}
      <div><div class="label"></div><div class="description"></div></div>
      <div class="drag">::</div>
    `;
    row.querySelector(".label").textContent = option.label;
    setDescriptionControl(row, option);
    row.querySelector("input").addEventListener("change", event => {{
      if (event.target.checked) {{
        selected.add(option.id);
      }} else {{
        selected.delete(option.id);
      }}
      row.classList.toggle("selected", event.target.checked);
    }});
    row.addEventListener("click", event => {{
      if (event.target.closest("input, textarea")) return;
      toggle(option.id);
    }});
    row.addEventListener("dragstart", () => {{ dragId = option.id; row.classList.add("dragging"); }});
    row.addEventListener("dragend", () => row.classList.remove("dragging"));
    row.addEventListener("dragover", event => event.preventDefault());
    row.addEventListener("drop", event => {{
      event.preventDefault();
      moveBefore(dragId, option.id);
    }});
    listEl.append(row);
  }});
}}

function controlHtml(option, index) {{
  return `<input type="checkbox" ${{selected.has(option.id) ? "checked" : ""}}>`;
}}

function setDescriptionControl(row, option) {{
  const container = row.querySelector(".description");
  if (!DATA.editDescriptions) {{
    container.textContent = option.description || "";
    return;
  }}
  const textarea = document.createElement("textarea");
  textarea.className = "description";
  textarea.value = option.description || "";
  textarea.dataset.field = "description";
  textarea.addEventListener("input", event => {{
    option.description = event.target.value;
  }});
  container.replaceWith(textarea);
}}

function toggle(id) {{
  selected.has(id) ? selected.delete(id) : selected.add(id);
  render();
}}

function moveBefore(fromId, toId) {{
  if (!fromId || fromId === toId) return;
  const next = ordered.filter(id => id !== fromId);
  next.splice(next.indexOf(toId), 0, fromId);
  ordered = next;
  render();
}}

function currentState() {{
  const rows = [...listEl.querySelectorAll(".option")];
  const selectedIds = rows
    .filter(row => row.querySelector("input").checked)
    .map(row => row.dataset.id);
  const orderedIds = rows
    .map(row => row.dataset.id)
    .filter(id => selectedIds.includes(id));
  const descriptions = Object.fromEntries(rows.map(row => [
    row.dataset.id,
    row.querySelector('[data-field="description"]')?.value ?? DATA.options.find(option => option.id === row.dataset.id)?.description ?? ""
  ]));
  selected = new Set(selectedIds);
  ordered = rows.map(row => row.dataset.id);
  return {{ selected: selectedIds, ordered: orderedIds, descriptions }};
}}

async function finish(cancelled) {{
  const state = currentState();
  const payload = {{
    selected: state.selected,
    ordered: state.ordered,
    descriptions: state.descriptions,
    cancelled
  }};
  await fetch("/submit", {{ method: "POST", headers: {{ "Content-Type": "application/json" }}, body: JSON.stringify(payload) }});
  document.body.innerHTML = "<main><h1>Submitted</h1><p class='hint'>You can close this tab.</p></main>";
}}

submitEl.addEventListener("click", () => finish(false));
cancelEl.addEventListener("click", () => finish(true));
render();
</script>
</body>
</html>"""


def _html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _error_result(message: str) -> dict[str, Any]:
    return {
        "mode": "multi_select_reorder",
        "selected": [],
        "ordered": [],
        "cancelled": True,
        "error": message,
    }


@mcp.tool()
def multi_select_reorder(
    title: str,
    options: list[Any],
    initial_selected: list[Any] | None = None,
    edit_descriptions: bool = False,
) -> dict[str, Any]:
    """Open a web UI to select multiple options and reorder them by drag-and-drop.

    Options are selected by default. Pass option objects with selected=false or
    pass initial_selected with option ids to override the initial state. Options
    can also be compact tuples/lists: [id, label, description, selected].
    Set edit_descriptions=true to edit descriptions in the same browser window.
    """
    return _select(
        title,
        options,
        initial_selected=initial_selected,
        edit_descriptions=edit_descriptions,
    )


if __name__ == "__main__":
    mcp.run()
