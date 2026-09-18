"""SQLite 저장소. 메시지는 앱 구분 없이 하나의 테이블에 정규화해서 넣는다."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable

from parser import Message

DB_PATH = Path(__file__).parent / "data" / "coach.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    app     TEXT NOT NULL,
    room    TEXT NOT NULL,
    sender  TEXT NOT NULL,
    text    TEXT NOT NULL,
    ts      TEXT NOT NULL,           -- ISO8601
    UNIQUE(app, room, sender, ts, text) ON CONFLICT IGNORE
);
CREATE INDEX IF NOT EXISTS idx_msg_room_ts ON messages(room, ts);
CREATE INDEX IF NOT EXISTS idx_msg_sender  ON messages(sender);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def insert_messages(con: sqlite3.Connection, msgs: Iterable[Message]) -> int:
    rows = [(m.app, m.room, m.sender, m.text, m.ts.isoformat()) for m in msgs]
    cur = con.executemany(
        "INSERT INTO messages(app, room, sender, text, ts) VALUES (?,?,?,?,?)", rows)
    con.commit()
    return cur.rowcount if cur.rowcount >= 0 else len(rows)


def all_messages(con: sqlite3.Connection, room: str | None = None) -> list[Message]:
    q = "SELECT id, app, room, sender, text, ts FROM messages"
    args: tuple = ()
    if room:
        q += " WHERE room = ?"
        args = (room,)
    q += " ORDER BY ts"
    return [Message(r["room"], r["sender"], r["text"], datetime.fromisoformat(r["ts"]), r["app"], r["id"])
            for r in con.execute(q, args)]


def messages_by_ids(con: sqlite3.Connection, ids: list[int]) -> list[Message]:
    if not ids:
        return []
    qs = ",".join("?" * len(ids))
    return [Message(r["room"], r["sender"], r["text"], datetime.fromisoformat(r["ts"]), r["app"], r["id"])
            for r in con.execute(f"SELECT id, app, room, sender, text, ts FROM messages WHERE id IN ({qs}) ORDER BY ts", ids)]


def messages_around(con: sqlite3.Connection, msg_id: int, k: int = 10) -> list[Message]:
    r = con.execute("SELECT room, ts FROM messages WHERE id = ?", (msg_id,)).fetchone()
    if not r:
        return []
    before = con.execute("SELECT id, app, room, sender, text, ts FROM messages WHERE room=? AND ts<=? AND id<>? ORDER BY ts DESC LIMIT ?",
                         (r["room"], r["ts"], msg_id, k)).fetchall()
    after = con.execute("SELECT id, app, room, sender, text, ts FROM messages WHERE room=? AND ts>=? AND id<>? ORDER BY ts ASC LIMIT ?",
                        (r["room"], r["ts"], msg_id, k)).fetchall()
    mid = con.execute("SELECT id, app, room, sender, text, ts FROM messages WHERE id=?", (msg_id,)).fetchall()
    rows = sorted(list(before) + mid + list(after), key=lambda x: (x["ts"], x["id"]))
    return [Message(x["room"], x["sender"], x["text"], datetime.fromisoformat(x["ts"]), x["app"], x["id"]) for x in rows]


def now_ts(con: sqlite3.Connection) -> datetime:
    """미답장 판정용 '현재': 업로드된 파일들의 저장한 날짜 중 최댓값, 없으면 데이터 마지막 시각."""
    v = get_setting(con, "saved_at")
    if v:
        return datetime.fromisoformat(v)
    r = con.execute("SELECT MAX(ts) AS m FROM messages").fetchone()
    return datetime.fromisoformat(r["m"]) if r and r["m"] else datetime.now()


def bump_saved_at(con: sqlite3.Connection, saved: datetime) -> None:
    cur = get_setting(con, "saved_at")
    if not cur or datetime.fromisoformat(cur) < saved:
        set_setting(con, "saved_at", saved.isoformat())


def rooms(con: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in con.execute(
        "SELECT room, COUNT(*) AS n, MIN(ts) AS first_ts, MAX(ts) AS last_ts "
        "FROM messages GROUP BY room ORDER BY n DESC")]


def senders(con: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in con.execute(
        "SELECT sender, COUNT(*) AS n FROM messages GROUP BY sender ORDER BY n DESC")]


def get_setting(con: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    r = con.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return r["value"] if r else default


def set_setting(con: sqlite3.Connection, key: str, value: str) -> None:
    con.execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?,?)", (key, value))
    con.commit()


def clear(con: sqlite3.Connection) -> None:
    con.execute("DELETE FROM messages")
    con.commit()
