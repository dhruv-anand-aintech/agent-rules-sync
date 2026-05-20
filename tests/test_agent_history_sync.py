import json
import sqlite3
from pathlib import Path

from agent_history_sync import AgentCommand, AgentHistorySync


def _make_history_db(path: Path, with_author: bool = False):
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    cols = """
        id text primary key,
        timestamp integer not null,
        duration integer not null,
        exit integer not null,
        command text not null,
        cwd text not null,
        session text not null,
        hostname text not null,
        deleted_at integer
    """
    if with_author:
        cols += ", author text, intent text"
    conn.execute(f"create table history ({cols}, unique(timestamp, cwd, command))")
    conn.commit()
    conn.close()


def test_imports_agent_command_to_legacy_atuin_with_platform_tag(tmp_path):
    db = tmp_path / ".local" / "share" / "atuin" / "history.db"
    _make_history_db(db)

    sync = AgentHistorySync(config_dir=tmp_path / ".config" / "agent-rules-sync")
    sync.home = tmp_path
    sync.atuin_db = db
    sync.hostname = "host:user"

    cmd = AgentCommand(
        source="transcript.jsonl",
        platform="codex",
        session="s1",
        timestamp_ns=123,
        command="git status",
        cwd="/repo",
    )

    assert sync._insert_atuin([cmd], dry_run=False) == 1

    conn = sqlite3.connect(str(db))
    row = conn.execute("select command, cwd, session from history").fetchone()
    conn.close()

    assert row == ("git status # agent:codex", "/repo", "agent:codex:s1")


def test_imports_agent_command_to_new_atuin_author_columns(tmp_path):
    db = tmp_path / ".local" / "share" / "atuin" / "history.db"
    _make_history_db(db, with_author=True)

    sync = AgentHistorySync(config_dir=tmp_path / ".config" / "agent-rules-sync")
    sync.home = tmp_path
    sync.atuin_db = db
    sync.hostname = "host:user"

    cmd = AgentCommand(
        source="transcript.jsonl",
        platform="claude-code",
        session="s1",
        timestamp_ns=456,
        command="npm test",
        cwd="/repo",
        intent="run tests",
    )

    assert sync._insert_atuin([cmd], dry_run=False) == 1

    conn = sqlite3.connect(str(db))
    row = conn.execute("select command, author, intent from history").fetchone()
    conn.close()

    assert row == ("npm test", "claude-code", "run tests")


def test_extracts_codex_exec_command(tmp_path):
    home = tmp_path
    session_dir = home / ".codex" / "sessions" / "2026" / "05" / "20"
    session_dir.mkdir(parents=True)
    transcript = session_dir / "rollout-test.jsonl"
    transcript.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "timestamp": "2026-05-20T00:00:00Z",
                        "type": "session_meta",
                        "payload": {"id": "sid", "cwd": "/repo"},
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-05-20T00:00:01Z",
                        "type": "response_item",
                        "payload": {
                            "type": "custom_tool_call",
                            "name": "functions.exec_command",
                            "input": json.dumps({"cmd": "git status", "workdir": "/repo/sub"}),
                        },
                    }
                ),
            ]
        )
        + "\n"
    )

    sync = AgentHistorySync(config_dir=home / ".config" / "agent-rules-sync")
    sync.home = home

    commands = list(sync._iter_codex())

    assert len(commands) == 1
    assert commands[0].platform == "codex"
    assert commands[0].session == "sid"
    assert commands[0].command == "git status"
    assert commands[0].cwd == "/repo/sub"


def test_extracts_cursor_command_timestamp_from_bubble_metadata(tmp_path):
    home = tmp_path
    session_id = "1a0a5012-7b28-4181-bfff-461c37ebb4b1"
    transcript_dir = (
        home
        / ".cursor"
        / "projects"
        / "Users-dhruvanand-Code-demo"
        / "agent-transcripts"
        / session_id
    )
    transcript_dir.mkdir(parents=True)
    transcript = transcript_dir / f"{session_id}.jsonl"
    transcript.write_text(
        "\n".join(
            [
                json.dumps({"role": "user", "message": {"content": [{"type": "text", "text": "run ls"}]}}),
                json.dumps(
                    {
                        "role": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "name": "terminal",
                                    "input": {"command": "ls -la", "cwd": "/repo"},
                                }
                            ]
                        },
                    }
                ),
            ]
        )
        + "\n"
    )

    cursor_db = home / "state.vscdb"
    conn = sqlite3.connect(str(cursor_db))
    conn.execute("create table cursorDiskKV (key text primary key, value text)")
    conn.execute(
        "insert into cursorDiskKV(key, value) values(?, ?)",
        (
            f"composerData:{session_id}",
            json.dumps(
                {
                    "createdAt": 1777884640426,
                    "fullConversationHeadersOnly": [
                        {"bubbleId": "user-bubble"},
                        {"bubbleId": "assistant-bubble"},
                    ],
                }
            ),
        ),
    )
    conn.execute(
        "insert into cursorDiskKV(key, value) values(?, ?)",
        (
            f"bubbleId:{session_id}:user-bubble",
            json.dumps({"createdAt": "2026-05-04T08:50:40.585Z"}),
        ),
    )
    conn.execute(
        "insert into cursorDiskKV(key, value) values(?, ?)",
        (
            f"bubbleId:{session_id}:assistant-bubble",
            json.dumps({"createdAt": "2026-05-04T08:50:46.064Z"}),
        ),
    )
    conn.commit()
    conn.close()

    sync = AgentHistorySync(config_dir=home / ".config" / "agent-rules-sync")
    sync.home = home
    sync.cursor_state_db = cursor_db

    commands = list(sync._iter_cursor_cli_file(transcript))

    assert len(commands) == 1
    assert commands[0].platform == "cursor"
    assert commands[0].command == "ls -la"
    assert commands[0].timestamp_ns == 1777884646064000000


def test_sync_can_import_only_changed_transcript_paths(tmp_path):
    home = tmp_path
    db = home / ".local" / "share" / "atuin" / "history.db"
    _make_history_db(db)

    codex_dir = home / ".codex" / "sessions" / "2026" / "05" / "21"
    codex_dir.mkdir(parents=True)
    first = codex_dir / "first.jsonl"
    second = codex_dir / "second.jsonl"
    for path, command in [(first, "git status"), (second, "npm test")]:
        path.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "timestamp": "2026-05-21T00:00:00Z",
                            "type": "session_meta",
                            "payload": {"id": path.stem, "cwd": "/repo"},
                        }
                    ),
                    json.dumps(
                        {
                            "timestamp": "2026-05-21T00:00:01Z",
                            "type": "response_item",
                            "payload": {
                                "type": "custom_tool_call",
                                "name": "functions.exec_command",
                                "input": json.dumps({"cmd": command, "workdir": "/repo"}),
                            },
                        }
                    ),
                ]
            )
            + "\n"
        )

    sync = AgentHistorySync(config_dir=home / ".config" / "agent-rules-sync")
    sync.home = home
    sync.atuin_db = db
    sync.hostname = "host:user"

    result = sync.sync(paths=[second])

    assert result["found"] == 1
    assert result["imported"] == 1
    conn = sqlite3.connect(str(db))
    rows = conn.execute("select command from history").fetchall()
    conn.close()
    assert rows == [("npm test # agent:codex",)]


def test_history_changed_reports_new_and_modified_transcripts(tmp_path):
    home = tmp_path
    transcript = home / ".codex" / "sessions" / "2026" / "05" / "21" / "rollout.jsonl"
    transcript.parent.mkdir(parents=True)

    sync = AgentHistorySync(config_dir=home / ".config" / "agent-rules-sync")
    sync.home = home
    hashes = sync.get_watch_paths_and_hashes()
    assert hashes == {}

    transcript.write_text("{}\n")
    changed = sync.history_changed(hashes)
    assert changed == [transcript]
    assert transcript in hashes

    transcript.write_text("{}\n{}\n")
    changed = sync.history_changed(hashes)
    assert changed == [transcript]
