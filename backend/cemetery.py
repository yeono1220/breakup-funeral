"""공동묘지: 묘비·헌화·방명록. 로그인 없음 — 브라우저가 만든 익명 ID(anon)로만 중복 헌화를 막는다."""
from __future__ import annotations

import sqlite3
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS tombs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    epitaph   TEXT NOT NULL,
    kind      TEXT NOT NULL DEFAULT 'chrys',      -- chrys | curse
    days      INTEGER,                             -- 향년
    hanja     TEXT,                                -- 저주봉인이면 부적 사자성어
    owner     TEXT,                                -- 안치한 익명 ID
    flowers   INTEGER NOT NULL DEFAULT 0,
    created   TEXT NOT NULL,
    seed      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS flowers (
    tomb_id INTEGER NOT NULL, anon TEXT NOT NULL, created TEXT NOT NULL,
    PRIMARY KEY (tomb_id, anon)
);
CREATE TABLE IF NOT EXISTS guestbook (
    id INTEGER PRIMARY KEY AUTOINCREMENT, tomb_id INTEGER NOT NULL, anon TEXT NOT NULL,
    nick TEXT NOT NULL, text TEXT NOT NULL, created TEXT NOT NULL
);
"""

SEED = [
    ('"3년 연애 후 \'우리 잠깐 시간을 갖자\' → 잠수"', "curse", 1095, "來去無常", 2914),
    ('"청첩장 돌리기 3주 전 파혼"', "curse", 1460, "前緣已斷 後悔未斷", 2105),
    ('"200일 선물 주고 그날 밤 환승 발각"', "chrys", 200, None, 1888),
    ('"바쁘다며 스토리는 1분마다 올리던 그대"', "curse", 240, "戀愛即逃", 142),
    ('"읽씹 6시간, 답장은 \'ㅇㅇ\' 두 글자"', "chrys", 98, None, 88),
    ('"나만 좋아했던 것 같은 6개월"', "curse", 180, "前任常思", 231),
    ('"먼저 좋다 해놓고 먼저 식은 사람"', "chrys", 130, None, 67),
]
SEED_COMMENTS = ["저도 똑같이 당했어요… 힘내세요 🥺", "읽씹은 답장이 맞습니다. 잘 보내주세요", "당신의 앞날을 빕니다 🙏"]


def init(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    if con.execute("SELECT COUNT(*) FROM tombs").fetchone()[0] == 0:
        now = datetime.now().isoformat(timespec="seconds")
        for ep, kind, days, hanja, fl in SEED:
            cur = con.execute("INSERT INTO tombs(epitaph, kind, days, hanja, owner, flowers, created, seed) VALUES (?,?,?,?,?,?,?,1)",
                              (ep, kind, days, hanja, "seed", fl, now))
            for i, c in enumerate(SEED_COMMENTS[: 1 + (cur.lastrowid or 0) % 3]):
                con.execute("INSERT INTO guestbook(tomb_id, anon, nick, text, created) VALUES (?,?,?,?,?)",
                            (cur.lastrowid, f"seed{i}", "익명의 조문객", c, now))
        con.commit()


def _nick(anon: str) -> str:
    return f"익명의 조문객 #{(abs(hash(anon)) % 900) + 100}"


def list_tombs(con: sqlite3.Connection, anon: str | None) -> dict:
    init(con)
    rows = con.execute("""SELECT t.*, (SELECT COUNT(*) FROM guestbook g WHERE g.tomb_id = t.id) AS comments
                          FROM tombs t ORDER BY t.created DESC, t.id DESC""").fetchall()
    mine_flowered = {r[0] for r in con.execute("SELECT tomb_id FROM flowers WHERE anon = ?", (anon or "",))}
    tombs = [{"id": r["id"], "epitaph": r["epitaph"], "kind": r["kind"], "days": r["days"], "hanja": r["hanja"],
              "flowers": r["flowers"], "comments": r["comments"], "mine": bool(anon) and r["owner"] == anon,
              "flowered": r["id"] in mine_flowered, "created": r["created"]} for r in rows]
    top = sorted(tombs, key=lambda t: -t["flowers"])[:3]
    visitors = 100 + con.execute("SELECT COUNT(*) FROM flowers").fetchone()[0] + con.execute("SELECT COUNT(*) FROM guestbook").fetchone()[0]
    return {"tombs": tombs, "top": top, "visitors": visitors}


def bury(con: sqlite3.Connection, anon: str, epitaph: str, kind: str, days: int | None, hanja: str | None) -> dict:
    init(con)
    ex = con.execute("SELECT id FROM tombs WHERE owner = ? AND epitaph = ?", (anon, epitaph)).fetchone()
    if ex:
        return {"id": ex["id"], "existed": True}
    cur = con.execute("INSERT INTO tombs(epitaph, kind, days, hanja, owner, flowers, created) VALUES (?,?,?,?,?,0,?)",
                      (epitaph[:120], kind if kind in ("chrys", "curse") else "chrys", days, hanja, anon, datetime.now().isoformat(timespec="seconds")))
    con.commit()
    return {"id": cur.lastrowid, "existed": False}


def flower(con: sqlite3.Connection, tomb_id: int, anon: str) -> dict:
    init(con)
    try:
        con.execute("INSERT INTO flowers(tomb_id, anon, created) VALUES (?,?,?)", (tomb_id, anon, datetime.now().isoformat(timespec="seconds")))
    except sqlite3.IntegrityError:
        r = con.execute("SELECT flowers FROM tombs WHERE id = ?", (tomb_id,)).fetchone()
        return {"flowers": r["flowers"] if r else 0, "already": True}
    con.execute("UPDATE tombs SET flowers = flowers + 1 WHERE id = ?", (tomb_id,))
    con.commit()
    r = con.execute("SELECT flowers FROM tombs WHERE id = ?", (tomb_id,)).fetchone()
    return {"flowers": r["flowers"] if r else 0, "already": False}


def comments(con: sqlite3.Connection, tomb_id: int) -> list[dict]:
    init(con)
    return [dict(r) for r in con.execute("SELECT id, nick, text, created FROM guestbook WHERE tomb_id = ? ORDER BY id DESC LIMIT 100", (tomb_id,))]


def add_comment(con: sqlite3.Connection, tomb_id: int, anon: str, text: str) -> dict:
    init(con)
    text = text.strip()[:200]
    if not text:
        raise ValueError("empty")
    nick = _nick(anon)
    con.execute("INSERT INTO guestbook(tomb_id, anon, nick, text, created) VALUES (?,?,?,?,?)",
                (tomb_id, anon, nick, text, datetime.now().isoformat(timespec="seconds")))
    con.commit()
    return {"nick": nick, "text": text}
