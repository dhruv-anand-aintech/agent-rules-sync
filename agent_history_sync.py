#!/usr/bin/env python3
"""Import coding-agent shell commands into Atuin history."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator


@dataclass(frozen=True)
class AgentCommand:
    source: str
    platform: str
    session: str
    timestamp_ns: int
    command: str
    cwd: str
    exit_code: int = -1
    duration_ns: int = -1
    intent: str | None = None

    @property
    def key(self) -> str:
        raw = "\0".join(
            [
                self.source,
                self.platform,
                self.session,
                str(self.timestamp_ns),
                self.cwd,
                self.command,
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AgentHistorySync:
    """Extract commands from agent transcripts and add them to Atuin."""

    def __init__(self, config_dir: Path | None = None):
        self.home = Path.home()
        self.config_dir = config_dir or (self.home / ".config" / "agent-rules-sync")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.config_dir / "agent_history_state.json"
        self.log_file = self.config_dir / "agent-command-history.jsonl"
        self.atuin_db = self.home / ".local" / "share" / "atuin" / "history.db"
        self.cursor_state_db = (
            self.home
            / "Library"
            / "Application Support"
            / "Cursor"
            / "User"
            / "globalStorage"
            / "state.vscdb"
        )
        self.cursor_workspace_dir = (
            self.home
            / "Library"
            / "Application Support"
            / "Cursor"
            / "User"
            / "workspaceStorage"
        )
        self._cursor_bubble_timestamp_cache: dict[str, list[int]] = {}
        self.hostname = f"{socket.gethostname()}:{os.environ.get('USER', 'agent')}"

    def sync(
        self,
        log_callback=None,
        dry_run: bool = False,
        paths: Iterable[Path | str] | None = None,
    ) -> dict[str, int]:
        log = log_callback or (lambda _: None)
        state = self._load_state()
        commands = list(self.iter_commands(paths=paths))

        new_commands = [cmd for cmd in commands if cmd.key not in state]
        if not new_commands:
            return {"found": len(commands), "imported": 0}

        self._append_jsonl(new_commands, dry_run=dry_run)

        imported = 0
        if self.atuin_db.exists():
            imported = self._insert_atuin(new_commands, dry_run=dry_run)
        else:
            log(f"[history] Atuin DB not found at {self.atuin_db}; wrote JSONL only")

        if not dry_run:
            for cmd in new_commands:
                state[cmd.key] = {
                    "platform": cmd.platform,
                    "source": cmd.source,
                    "timestamp_ns": cmd.timestamp_ns,
                }
            self._save_state(state)

        return {"found": len(commands), "imported": imported}

    def iter_commands(self, paths: Iterable[Path | str] | None = None) -> Iterator[AgentCommand]:
        if paths is not None:
            seen = set()
            for raw_path in paths:
                path = Path(raw_path).expanduser()
                if path in seen or not path.is_file():
                    continue
                seen.add(path)
                yield from self._iter_path(path)
            return

        yield from self._iter_codex()
        yield from self._iter_claude()
        yield from self._iter_cursor_ide()
        yield from self._iter_cursor_cli()
        yield from self._iter_gemini()
        yield from self._iter_opencode()
        yield from self._iter_hermes()
        yield from self._iter_openclaw()

    def get_watch_paths_and_hashes(self) -> dict[Path, str | None]:
        return {path: self._path_signature(path) for path in self.transcript_paths()}

    def history_changed(self, old_hashes: dict[Path, str | None]) -> list[Path]:
        current = self.get_watch_paths_and_hashes()
        changed = [
            path
            for path, signature in current.items()
            if signature != old_hashes.get(path)
        ]
        removed = [path for path in old_hashes if path not in current]
        old_hashes.clear()
        old_hashes.update(current)
        return changed + removed

    def transcript_roots(self) -> list[Path]:
        roots = [
            self.home / ".codex" / "sessions",
            self.home / ".claude" / "projects",
            self.home / ".cursor" / "projects",
            self.home / ".gemini" / "tmp",
            self.home / ".local" / "share" / "opencode",
            self.home / ".hermes",
            self.home / ".openclaw" / "agents",
        ]
        return [root for root in roots if root.exists()]

    def transcript_paths(self) -> list[Path]:
        paths = []
        for root, pattern in [
            (self.home / ".codex" / "sessions", "*.jsonl"),
            (self.home / ".claude" / "projects", "*.jsonl"),
            (self.home / ".cursor" / "projects", "*.jsonl"),
            (self.home / ".gemini" / "tmp", "*.jsonl"),
            (self.home / ".openclaw" / "agents", "*.jsonl"),
        ]:
            paths.extend(self._recent_files(root, pattern))
        for path in [
            self.home / ".local" / "share" / "opencode" / "opencode.db",
            self.home / ".hermes" / "state.db",
        ]:
            if path.exists():
                paths.append(path)
        return sorted(set(paths), key=lambda p: str(p))

    def _iter_path(self, path: Path) -> Iterator[AgentCommand]:
        parts = set(path.parts)
        if ".codex" in parts and "sessions" in parts:
            yield from self._iter_codex_file(path)
        elif ".claude" in parts and "projects" in parts:
            yield from self._iter_claude_file(path)
        elif ".cursor" in parts and "projects" in parts:
            yield from self._iter_cursor_cli_file(path)
        elif ".gemini" in parts and "tmp" in parts:
            yield from self._iter_gemini_file(path)
        elif path.name == "opencode.db" and "opencode" in parts:
            yield from self._iter_opencode_file(path)
        elif path.name == "state.db" and ".hermes" in parts:
            yield from self._iter_hermes_file(path)
        elif ".openclaw" in parts and "agents" in parts:
            yield from self._iter_openclaw_file(path)

    def _load_state(self) -> dict:
        if not self.state_file.exists():
            return {}
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_state(self, state: dict) -> None:
        self.state_file.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _append_jsonl(self, commands: Iterable[AgentCommand], dry_run: bool) -> None:
        if dry_run:
            return
        with self.log_file.open("a", encoding="utf-8") as f:
            for cmd in commands:
                f.write(
                    json.dumps(
                        {
                            "id": cmd.key,
                            "platform": cmd.platform,
                            "session": cmd.session,
                            "timestamp_ns": cmd.timestamp_ns,
                            "command": cmd.command,
                            "cwd": cmd.cwd,
                            "exit_code": cmd.exit_code,
                            "duration_ns": cmd.duration_ns,
                            "intent": cmd.intent,
                            "source": cmd.source,
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )

    def _insert_atuin(self, commands: Iterable[AgentCommand], dry_run: bool) -> int:
        rows = list(commands)
        if dry_run or not rows:
            return len(rows)

        conn = sqlite3.connect(str(self.atuin_db))
        try:
            columns = {
                row[1]
                for row in conn.execute("pragma table_info(history)").fetchall()
            }
            has_author = "author" in columns
            has_intent = "intent" in columns
            inserted = 0

            for cmd in rows:
                history_id = self._history_id(cmd)
                stored_command = self._tagged_command(cmd, has_author=has_author)
                session = f"agent:{cmd.platform}:{cmd.session}"
                if has_author:
                    base_cols = [
                        "id",
                        "timestamp",
                        "duration",
                        "exit",
                        "command",
                        "cwd",
                        "session",
                        "hostname",
                        "author",
                    ]
                    values = [
                        history_id,
                        cmd.timestamp_ns,
                        cmd.duration_ns,
                        cmd.exit_code,
                        stored_command,
                        cmd.cwd,
                        session,
                        self.hostname,
                        cmd.platform,
                    ]
                    if has_intent:
                        base_cols.append("intent")
                        values.append(cmd.intent)
                    placeholders = ", ".join("?" for _ in base_cols)
                    sql = (
                        f"insert or ignore into history({', '.join(base_cols)}) "
                        f"values({placeholders})"
                    )
                else:
                    sql = (
                        "insert or ignore into history"
                        "(id, timestamp, duration, exit, command, cwd, session, hostname) "
                        "values(?, ?, ?, ?, ?, ?, ?, ?)"
                    )
                    values = [
                        history_id,
                        cmd.timestamp_ns,
                        cmd.duration_ns,
                        cmd.exit_code,
                        stored_command,
                        cmd.cwd,
                        session,
                        self.hostname,
                    ]

                before = conn.total_changes
                conn.execute(sql, values)
                inserted += conn.total_changes - before

            conn.commit()
            return inserted
        finally:
            conn.close()

    @staticmethod
    def _history_id(cmd: AgentCommand) -> str:
        # Atuin history IDs are UUID-like strings, but the schema only requires text.
        return "agent_" + cmd.key[:26]

    @staticmethod
    def _tagged_command(cmd: AgentCommand, has_author: bool) -> str:
        if has_author:
            return cmd.command
        tag = f"# agent:{cmd.platform}"
        if cmd.command.rstrip().endswith(tag):
            return cmd.command
        return f"{cmd.command.rstrip()} {tag}"

    def _iter_codex(self) -> Iterator[AgentCommand]:
        root = self.home / ".codex" / "sessions"
        if not root.exists():
            return

        for path in self._recent_files(root, "*.jsonl"):
            yield from self._iter_codex_file(path)

    def _iter_codex_file(self, path: Path) -> Iterator[AgentCommand]:
        session = path.stem
        cwd = str(self.home)
        for line in self._read_lines(path):
            try:
                event = json.loads(line)
            except Exception:
                continue

            ts = self._timestamp_ns(event.get("timestamp"))
            if event.get("type") == "session_meta":
                payload = event.get("payload") or {}
                session = payload.get("id") or session
                cwd = payload.get("cwd") or cwd
                continue

            payload = event.get("payload") or {}
            if event.get("type") != "response_item":
                continue
            if payload.get("type") not in {"custom_tool_call", "function_call"}:
                continue

            name = str(payload.get("name") or "")
            if "exec_command" not in name and name not in {"shell", "bash"}:
                continue

            parsed = self._parse_jsonish(payload.get("input") or payload.get("arguments"))
            command = parsed.get("cmd") or parsed.get("command")
            if not command:
                continue
            command_cwd = parsed.get("workdir") or cwd
            yield AgentCommand(
                source=str(path),
                platform="codex",
                session=session,
                timestamp_ns=ts,
                command=str(command),
                cwd=str(command_cwd),
                intent=name,
            )

    def _iter_claude(self) -> Iterator[AgentCommand]:
        root = self.home / ".claude" / "projects"
        if not root.exists():
            return

        for path in self._recent_files(root, "*.jsonl"):
            yield from self._iter_claude_file(path)

    def _iter_claude_file(self, path: Path) -> Iterator[AgentCommand]:
        session = path.stem
        cwd = self._cwd_from_claude_path(path)
        for line in self._read_lines(path):
            try:
                event = json.loads(line)
            except Exception:
                continue
            ts = self._timestamp_ns(event.get("timestamp"))
            for block in self._content_blocks(event):
                if not isinstance(block, dict):
                    continue
                name = str(block.get("name") or "")
                if block.get("type") != "tool_use" or name.lower() != "bash":
                    continue
                payload = block.get("input") or {}
                command = payload.get("command")
                if not command:
                    continue
                yield AgentCommand(
                    source=str(path),
                    platform="claude-code",
                    session=session,
                    timestamp_ns=ts,
                    command=str(command),
                    cwd=cwd,
                    intent=payload.get("description"),
                )

    def _iter_cursor_cli(self) -> Iterator[AgentCommand]:
        root = self.home / ".cursor" / "projects"
        if not root.exists():
            return

        for path in self._recent_files(root, "*.jsonl"):
            yield from self._iter_cursor_cli_file(path)

    def _iter_cursor_cli_file(self, path: Path) -> Iterator[AgentCommand]:
        session = path.stem
        cwd = self._cwd_from_cursor_path(path)
        fallback_ts = self._file_timestamp_ns(path)
        bubble_timestamps = self._cursor_bubble_timestamps(session)
        for line_index, line in enumerate(self._read_lines(path)):
            try:
                event = json.loads(line)
            except Exception:
                continue
            line_ts = self._timestamp_ns_or_none(event.get("timestamp"))
            if line_ts is None and line_index < len(bubble_timestamps):
                line_ts = bubble_timestamps[line_index]
            ts = line_ts or fallback_ts
            offset = 0
            for obj in self._walk_json(event):
                if not isinstance(obj, dict):
                    continue
                command = obj.get("command") or obj.get("cmd")
                if not isinstance(command, str) or not command.strip():
                    continue
                marker = " ".join(str(v).lower() for v in obj.values() if isinstance(v, str))
                has_command_context = bool(obj.get("cwd") or obj.get("workdir"))
                if not has_command_context and not any(
                    word in marker for word in ["terminal", "shell", "bash", "exec"]
                ):
                    continue
                yield AgentCommand(
                    source=str(path),
                    platform="cursor",
                    session=session,
                    timestamp_ns=ts + offset,
                    command=command,
                    cwd=str(obj.get("cwd") or obj.get("workdir") or cwd),
                )
                offset += 1

    def _iter_cursor_ide(self) -> Iterator[AgentCommand]:
        if not self.cursor_state_db.exists():
            return
        workspace_map = self._cursor_composer_workspace_map()
        max_rows = 5000
        try:
            conn = sqlite3.connect(str(self.cursor_state_db))
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.execute(
                    """
                    select
                        substr(key, 10, 36) as composer_id,
                        json_extract(value, '$.bubbleId') as bubble_id,
                        json_extract(value, '$.toolFormerData.name') as tool_name,
                        json_extract(value, '$.toolFormerData.rawArgs') as raw_args,
                        coalesce(json_extract(value, '$.createdAt'), json_extract(value, '$.timestamp')) as timestamp
                    from cursorDiskKV
                    where key like 'bubbleId:%'
                      and json_extract(value, '$.toolFormerData.name') in ('run_terminal_command_v2', 'run_terminal_cmd')
                    order by key desc
                    limit ?
                    """,
                    (max_rows,),
                )
                rows = cursor.fetchall()
            finally:
                conn.close()
        except Exception:
            return

        session_offsets: dict[str, int] = {}
        composer_times = self._cursor_composer_times()
        for row in rows:
            parsed = self._parse_jsonish(row["raw_args"])
            command = parsed.get("command") or parsed.get("cmd")
            if not command:
                continue
            session = str(row["composer_id"])
            offset = session_offsets.get(session, 0)
            session_offsets[session] = offset + 1
            ts = self._timestamp_ns_or_none(row["timestamp"])
            if ts is None:
                created, updated = composer_times.get(session, (None, None))
                ts = updated or created or self._file_timestamp_ns(self.cursor_state_db)
            yield AgentCommand(
                source=str(self.cursor_state_db),
                platform="cursor",
                session=session,
                timestamp_ns=ts + offset,
                command=str(command),
                cwd=str(parsed.get("workdir") or parsed.get("cwd") or workspace_map.get(session) or self.home),
                intent=str(row["tool_name"] or "terminal"),
            )

    def _cursor_composer_times(self) -> dict[str, tuple[int | None, int | None]]:
        if not self.cursor_state_db.exists():
            return {}
        max_composers = 2000
        try:
            conn = sqlite3.connect(str(self.cursor_state_db))
            try:
                rows = conn.execute(
                    """
                    select
                        substr(key, 14) as composer_id,
                        json_extract(value, '$.createdAt') as created_at,
                        json_extract(value, '$.lastUpdatedAt') as updated_at
                    from cursorDiskKV
                    where key like 'composerData:%'
                    order by key desc
                    limit ?
                    """,
                    (max_composers,),
                ).fetchall()
            finally:
                conn.close()
        except Exception:
            return {}
        return {
            str(row[0]): (
                self._timestamp_ns_or_none(row[1]),
                self._timestamp_ns_or_none(row[2]),
            )
            for row in rows
            if row and row[0]
        }

    def _cursor_composer_workspace_map(self) -> dict[str, str]:
        out: dict[str, str] = {}
        if not self.cursor_workspace_dir.exists():
            return out
        for ws_dir in self.cursor_workspace_dir.iterdir():
            if not ws_dir.is_dir():
                continue
            workspace = ""
            try:
                data = json.loads((ws_dir / "workspace.json").read_text(encoding="utf-8"))
                workspace = str(data.get("folder") or "").replace("file://", "")
            except Exception:
                workspace = ""
            if not workspace:
                continue
            db = ws_dir / "state.vscdb"
            if not db.exists():
                continue
            try:
                conn = sqlite3.connect(str(db))
                try:
                    row = conn.execute(
                        "select value from ItemTable where key='composer.composerData' limit 1"
                    ).fetchone()
                finally:
                    conn.close()
                if not row:
                    continue
                data = json.loads(row[0])
                for composer in data.get("allComposers") or []:
                    composer_id = composer.get("composerId") if isinstance(composer, dict) else None
                    if composer_id:
                        out[str(composer_id)] = workspace
            except Exception:
                continue
        return out

    def _iter_gemini(self) -> Iterator[AgentCommand]:
        root = self.home / ".gemini" / "tmp"
        if not root.exists():
            return
        for path in self._recent_files(root, "*.jsonl"):
            yield from self._iter_gemini_file(path)

    def _iter_gemini_file(self, path: Path) -> Iterator[AgentCommand]:
        session = path.stem
        cwd = self._cwd_from_gemini_path(path)
        for line in self._read_lines(path):
            try:
                event = json.loads(line)
            except Exception:
                continue
            if event.get("sessionId"):
                session = str(event.get("sessionId") or session)
                continue
            ts = self._timestamp_ns(event.get("timestamp"))
            offset = 0
            for call in event.get("toolCalls") or []:
                if not isinstance(call, dict):
                    continue
                name = str(call.get("name") or "")
                if name != "run_shell_command":
                    continue
                args = call.get("args") or {}
                command = args.get("command") if isinstance(args, dict) else None
                if not command:
                    continue
                yield AgentCommand(
                    source=str(path),
                    platform="gemini",
                    session=session,
                    timestamp_ns=ts + offset,
                    command=str(command),
                    cwd=str(args.get("workdir") or args.get("cwd") or cwd),
                    intent=args.get("description") or name,
                )
                offset += 1

    def _iter_opencode(self) -> Iterator[AgentCommand]:
        path = self.home / ".local" / "share" / "opencode" / "opencode.db"
        if path.exists():
            yield from self._iter_opencode_file(path)

    def _iter_opencode_file(self, path: Path) -> Iterator[AgentCommand]:
        try:
            conn = sqlite3.connect(str(path))
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    select p.id, p.session_id, p.time_created, p.data, s.directory
                    from part p
                    left join session s on s.id = p.session_id
                    where p.data like '%"tool":"bash"%'
                       or p.data like '%"tool": "bash"%'
                    order by p.time_created, p.id
                    """
                ).fetchall()
            finally:
                conn.close()
        except Exception:
            return

        for row in rows:
            try:
                data = json.loads(row["data"])
            except Exception:
                continue
            if data.get("type") != "tool" or data.get("tool") != "bash":
                continue
            state = data.get("state") or {}
            input_data = state.get("input") or {}
            command = input_data.get("command") or input_data.get("cmd")
            if not command:
                continue
            time_data = state.get("time") or {}
            ts = self._timestamp_ns_or_none(time_data.get("start"))
            if ts is None:
                ts = self._timestamp_ns(row["time_created"])
            start = self._timestamp_ns_or_none(time_data.get("start"))
            end = self._timestamp_ns_or_none(time_data.get("end"))
            duration_ns = end - start if start is not None and end is not None and end >= start else -1
            metadata = state.get("metadata") or {}
            exit_code = metadata.get("exit")
            yield AgentCommand(
                source=str(path),
                platform="opencode",
                session=str(row["session_id"]),
                timestamp_ns=ts,
                command=str(command),
                cwd=str(input_data.get("workdir") or input_data.get("cwd") or row["directory"] or self.home),
                exit_code=int(exit_code if exit_code is not None else -1),
                duration_ns=duration_ns,
                intent=input_data.get("description") or state.get("title"),
            )

    def _iter_hermes(self) -> Iterator[AgentCommand]:
        path = self.home / ".hermes" / "state.db"
        if path.exists():
            yield from self._iter_hermes_file(path)

    def _iter_hermes_file(self, path: Path) -> Iterator[AgentCommand]:
        try:
            conn = sqlite3.connect(str(path))
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    select m.id, m.session_id, m.timestamp, m.tool_calls, s.source
                    from messages m
                    left join sessions s on s.id = m.session_id
                    where m.tool_calls is not null and m.tool_calls != ''
                    order by m.timestamp, m.id
                    """
                ).fetchall()
            finally:
                conn.close()
        except Exception:
            return

        for row in rows:
            try:
                calls = json.loads(row["tool_calls"])
            except Exception:
                continue
            if not isinstance(calls, list):
                continue
            offset = 0
            for call in calls:
                if not isinstance(call, dict):
                    continue
                function = call.get("function") or {}
                name = str(function.get("name") or call.get("name") or "")
                if name not in {"terminal", "bash", "shell", "exec"}:
                    continue
                parsed = self._parse_jsonish(function.get("arguments") or call.get("arguments"))
                command = parsed.get("command") or parsed.get("cmd")
                if not command:
                    continue
                yield AgentCommand(
                    source=str(path),
                    platform="hermes",
                    session=str(row["session_id"]),
                    timestamp_ns=self._timestamp_ns(row["timestamp"]) + offset,
                    command=str(command),
                    cwd=str(parsed.get("workdir") or parsed.get("cwd") or self.home),
                    intent=name,
                )
                offset += 1

    def _iter_openclaw(self) -> Iterator[AgentCommand]:
        root = self.home / ".openclaw" / "agents"
        if not root.exists():
            return
        for path in self._recent_files(root, "*.jsonl"):
            yield from self._iter_openclaw_file(path)

    def _iter_openclaw_file(self, path: Path) -> Iterator[AgentCommand]:
        session = path.stem
        cwd = str(self.home)
        agent_name = path.parts[-3] if len(path.parts) >= 3 else "main"
        for line in self._read_lines(path):
            try:
                event = json.loads(line)
            except Exception:
                continue
            if event.get("type") == "session":
                session = str(event.get("id") or session)
                cwd = str(event.get("cwd") or cwd)
                continue
            if event.get("type") != "message":
                continue
            msg = event.get("message") or {}
            if msg.get("role") != "assistant":
                continue
            ts = self._timestamp_ns(event.get("timestamp") or msg.get("timestamp"))
            offset = 0
            for block in msg.get("content") or []:
                if not isinstance(block, dict) or block.get("type") != "toolCall":
                    continue
                name = str(block.get("name") or "")
                if name not in {"exec", "terminal", "bash", "shell"}:
                    continue
                args = block.get("arguments") or {}
                command = args.get("command") or args.get("cmd") if isinstance(args, dict) else None
                if not command:
                    continue
                yield AgentCommand(
                    source=str(path),
                    platform="openclaw",
                    session=session,
                    timestamp_ns=ts + offset,
                    command=str(command),
                    cwd=str(args.get("workdir") or args.get("cwd") or cwd),
                    intent=f"{agent_name}:{name}",
                )
                offset += 1

    def _recent_files(self, root: Path, pattern: str, max_files: int = 100) -> list[Path]:
        if not root.exists():
            return []
        cutoff = time.time() - (30 * 24 * 60 * 60)
        try:
            files = [p for p in root.rglob(pattern) if p.is_file() and p.stat().st_mtime >= cutoff]
        except OSError:
            return []
        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[:max_files]

    @staticmethod
    def _path_signature(path: Path) -> str | None:
        try:
            stat = path.stat()
        except OSError:
            return None
        return f"{stat.st_size}:{stat.st_mtime_ns}"

    @staticmethod
    def _read_lines(path: Path) -> Iterator[str]:
        try:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                yield from f
        except OSError:
            return

    @staticmethod
    def _parse_jsonish(value) -> dict:
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return {}
        return {}

    @staticmethod
    def _content_blocks(event: dict) -> list:
        msg = event.get("message") or {}
        content = msg.get("content")
        if isinstance(content, list):
            return content
        if isinstance(content, dict):
            return [content]
        return []

    @staticmethod
    def _walk_json(value):
        yield value
        if isinstance(value, dict):
            for item in value.values():
                yield from AgentHistorySync._walk_json(item)
        elif isinstance(value, list):
            for item in value:
                yield from AgentHistorySync._walk_json(item)

    @staticmethod
    def _timestamp_ns(value) -> int:
        parsed = AgentHistorySync._timestamp_ns_or_none(value)
        return parsed if parsed is not None else time.time_ns()

    @staticmethod
    def _timestamp_ns_or_none(value) -> int | None:
        if isinstance(value, (int, float)):
            number = float(value)
            if number < 10_000_000_000:
                return int(number * 1_000_000_000)
            if number < 10_000_000_000_000:
                return int(number * 1_000_000)
            if number < 10_000_000_000_000_000:
                return int(number * 1_000)
            return int(number)
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return int(dt.timestamp() * 1_000_000_000)
            except ValueError:
                pass
        return None

    @staticmethod
    def _file_timestamp_ns(path: Path) -> int:
        try:
            return path.stat().st_mtime_ns
        except OSError:
            return time.time_ns()

    def _cursor_bubble_timestamps(self, session: str) -> list[int]:
        if session in self._cursor_bubble_timestamp_cache:
            return self._cursor_bubble_timestamp_cache[session]
        timestamps = self._load_cursor_bubble_timestamps(session)
        self._cursor_bubble_timestamp_cache[session] = timestamps
        return timestamps

    def _load_cursor_bubble_timestamps(self, session: str) -> list[int]:
        if not self.cursor_state_db.exists():
            return []

        try:
            conn = sqlite3.connect(str(self.cursor_state_db))
            try:
                row = conn.execute(
                    "select value from cursorDiskKV where key = ?",
                    (f"composerData:{session}",),
                ).fetchone()
                if not row:
                    return []
                composer = json.loads(row[0])
                headers = composer.get("fullConversationHeadersOnly") or []
                timestamps: list[int] = []
                for header in headers:
                    if not isinstance(header, dict):
                        timestamps.append(0)
                        continue
                    bubble_id = header.get("bubbleId")
                    if not bubble_id:
                        timestamps.append(0)
                        continue
                    bubble_row = conn.execute(
                        "select value from cursorDiskKV where key = ?",
                        (f"bubbleId:{session}:{bubble_id}",),
                    ).fetchone()
                    timestamp = None
                    if bubble_row:
                        try:
                            bubble = json.loads(bubble_row[0])
                            timestamp = self._timestamp_ns_or_none(
                                bubble.get("createdAt")
                                or bubble.get("timestamp")
                                or bubble.get("lastUpdatedAt")
                            )
                        except Exception:
                            timestamp = None
                    timestamps.append(timestamp or 0)

                composer_start = self._timestamp_ns_or_none(composer.get("createdAt")) or 0
                if composer_start:
                    timestamps = [ts or composer_start for ts in timestamps]
                return timestamps
            finally:
                conn.close()
        except Exception:
            return []

    @staticmethod
    def _cwd_from_claude_path(path: Path) -> str:
        try:
            slug = path.parent.name
            if slug.startswith("-"):
                return "/" + slug[1:].replace("-", "/")
        except Exception:
            pass
        return str(Path.home())

    @staticmethod
    def _cwd_from_cursor_path(path: Path) -> str:
        parts = path.parts
        try:
            idx = parts.index("projects")
            slug = parts[idx + 1]
            if slug.startswith("-"):
                return "/" + slug[1:].replace("-", "/")
        except Exception:
            pass
        return str(Path.home())

    def _cwd_from_gemini_path(self, path: Path) -> str:
        parts = path.parts
        try:
            idx = parts.index("tmp")
            slug = parts[idx + 1]
        except Exception:
            return str(self.home)

        projects_json = self.home / ".gemini" / "projects.json"
        try:
            data = json.loads(projects_json.read_text(encoding="utf-8"))
            for abs_path, mapped_slug in (data.get("projects") or {}).items():
                if mapped_slug == slug:
                    return str(abs_path)
        except Exception:
            pass
        return str(self.home / slug.replace("-", "/"))


def ensure_atuin_zsh(log_callback=None) -> bool:
    """Ensure zsh loads Atuin for reverse search."""
    log = log_callback or (lambda _: None)
    zshrc = Path.home() / ".zshrc"
    line = 'eval "$(atuin init zsh)"'
    if not zshrc.exists():
        zshrc.write_text(line + "\n", encoding="utf-8")
        return True
    text = zshrc.read_text(encoding="utf-8")
    if "atuin init zsh" in text:
        return False
    zshrc.write_text(text.rstrip() + "\n\n# Atuin shell history search\n" + line + "\n", encoding="utf-8")
    log("[history] enabled Atuin in ~/.zshrc; open a new shell or run `source ~/.zshrc`")
    return True


def ensure_atuin_installed(log_callback=None) -> bool:
    log = log_callback or (lambda _: None)
    if shutil_which("atuin"):
        return False
    if shutil_which("brew"):
        subprocess.run(["brew", "install", "atuin"], check=True)
        return True
    subprocess.run(
        ["sh", "-c", "curl --proto '=https' --tlsv1.2 -LsSf https://setup.atuin.sh | sh"],
        check=True,
    )
    log("[history] installed Atuin")
    return True


def shutil_which(command: str) -> str | None:
    from shutil import which

    return which(command)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import agent commands into Atuin history")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ensure-zsh", action="store_true")
    args = parser.parse_args(argv)

    ensure_atuin_installed(print)
    if args.ensure_zsh:
        ensure_atuin_zsh(print)

    result = AgentHistorySync().sync(log_callback=print, dry_run=args.dry_run)
    print(f"found={result['found']} imported={result['imported']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
