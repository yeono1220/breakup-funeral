"""카카오톡 대화 내보내기(txt) 파서.

지원 포맷 (자동 감지):
- Windows PC : "[홍길동] [오후 2:13] 안녕"  + 날짜 구분선 "--------------- 2024년 3월 5일 화요일 ---------------"
- Android    : "2024년 3월 5일 오후 2:13, 홍길동 : 안녕"
- iOS        : "2024. 3. 5. 오후 2:13, 홍길동 : 안녕"

실제 export 파일로 검증 후 패턴은 조정될 수 있음.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator


MEDIA_TOKENS = {"사진", "이모티콘", "동영상", "음성메시지", "파일", "샵검색"}


@dataclass
class Message:
    room: str
    sender: str
    text: str
    ts: datetime
    app: str = "kakao"
    id: int | None = None

    @property
    def is_media(self) -> bool:
        t = self.text.strip()
        return t in MEDIA_TOKENS or t.startswith("사진 ") and t.endswith("장")

    @property
    def n_chars(self) -> int:
        return 0 if self.is_media else len(self.text.strip())


# --- 공통 조각 -------------------------------------------------------------
_AMPM = r"(?P<ampm>오전|오후)"
_HM = r"(?P<h>\d{1,2}):(?P<m>\d{2})"
_DATE_KO = r"(?P<y>\d{4})년\s*(?P<mo>\d{1,2})월\s*(?P<d>\d{1,2})일"
_DATE_DOT = r"(?P<y>\d{4})\.\s*(?P<mo>\d{1,2})\.\s*(?P<d>\d{1,2})\."

# Windows PC
RE_PC_DATE = re.compile(rf"^-{{3,}}\s*{_DATE_KO}\s*\S*요일\s*-{{3,}}\s*$")
RE_PC_MSG = re.compile(rf"^\[(?P<sender>[^\]]+)\]\s*\[{_AMPM}\s*{_HM}\]\s?(?P<text>.*)$")

# Android
RE_AND_DATE = re.compile(rf"^{_DATE_KO}\s*\S*요일\s*$")
RE_AND_MSG = re.compile(rf"^{_DATE_KO}\s*{_AMPM}\s*{_HM},\s*(?P<sender>[^:]+?)\s*:\s?(?P<text>.*)$")

# iOS
RE_IOS_MSG = re.compile(rf"^{_DATE_DOT}\s*{_AMPM}\s*{_HM},\s*(?P<sender>[^:]+?)\s*:\s?(?P<text>.*)$")

# 헤더/시스템 라인
RE_HEADER_ROOM = re.compile(r"^(?P<room>.+?)\s*(님과|과의)?\s*카카오톡 대화\s*$")
RE_SAVED_AT = re.compile(r"^저장한 날짜\s*:\s*(?P<v>.+)$")
_RE_SAVED_ISO = re.compile(r"(?P<y>\d{4})-(?P<mo>\d{1,2})-(?P<d>\d{1,2})\s+(?P<H>\d{1,2}):(?P<M>\d{2})")
_RE_SAVED_KO = re.compile(rf"{_DATE_KO}\s*{_AMPM}\s*{_HM}")
_RE_SAVED_DOT = re.compile(rf"{_DATE_DOT}\s*{_AMPM}\s*{_HM}")


def parse_saved_at(lines: Iterable[str]) -> datetime | None:
    for line in list(lines)[:5]:
        m = RE_SAVED_AT.match(line.strip())
        if not m:
            continue
        v = m.group("v")
        if (x := _RE_SAVED_ISO.search(v)):
            return datetime(int(x["y"]), int(x["mo"]), int(x["d"]), int(x["H"]), int(x["M"]))
        for rx in (_RE_SAVED_KO, _RE_SAVED_DOT):
            if (x := rx.search(v)):
                return datetime(int(x["y"]), int(x["mo"]), int(x["d"]), _to_24h(x["ampm"], int(x["h"])), int(x["m"]))
    return None
SYSTEM_HINTS = ("님이 들어왔습니다", "님이 나갔습니다", "님을 초대했습니다", "채팅방 관리자가", "메시지가 삭제되었습니다")


def _to_24h(ampm: str, h: int) -> int:
    if ampm == "오전":
        return 0 if h == 12 else h
    return 12 if h == 12 else h + 12


def detect_format(lines: Iterable[str]) -> str:
    for line in lines:
        if RE_PC_MSG.match(line):
            return "pc"
        if RE_AND_MSG.match(line):
            return "android"
        if RE_IOS_MSG.match(line):
            return "ios"
    return "unknown"


def _room_from_header(lines: list[str], fallback: str) -> str:
    for line in lines[:5]:
        m = RE_HEADER_ROOM.match(line.strip())
        if m:
            return m.group("room").strip()
    return fallback


def parse_lines(lines: list[str], room_fallback: str = "") -> Iterator[Message]:
    fmt = detect_format(lines)
    room = _room_from_header(lines, room_fallback)
    cur_date: tuple[int, int, int] | None = None
    cur: Message | None = None

    def flush():
        nonlocal cur
        if cur is not None:
            cur.text = cur.text.rstrip("\n")
            yield_msg = cur
            cur = None
            return yield_msg
        return None

    for raw in lines:
        line = raw.rstrip("\n")
        if RE_SAVED_AT.match(line):
            continue

        if fmt == "pc":
            dm = RE_PC_DATE.match(line)
            if dm:
                cur_date = (int(dm["y"]), int(dm["mo"]), int(dm["d"]))
                if (m := flush()):
                    yield m
                continue
            mm = RE_PC_MSG.match(line)
            if mm and cur_date:
                if (m := flush()):
                    yield m
                ts = datetime(*cur_date, _to_24h(mm["ampm"], int(mm["h"])), int(mm["m"]))
                cur = Message(room, mm["sender"].strip(), mm["text"], ts)
                continue
        elif fmt == "android":
            if RE_AND_DATE.match(line):
                if (m := flush()):
                    yield m
                continue
            mm = RE_AND_MSG.match(line)
            if mm:
                if (m := flush()):
                    yield m
                ts = datetime(int(mm["y"]), int(mm["mo"]), int(mm["d"]),
                              _to_24h(mm["ampm"], int(mm["h"])), int(mm["m"]))
                cur = Message(room, mm["sender"].strip(), mm["text"], ts)
                continue
        elif fmt == "ios":
            mm = RE_IOS_MSG.match(line)
            if mm:
                if (m := flush()):
                    yield m
                ts = datetime(int(mm["y"]), int(mm["mo"]), int(mm["d"]),
                              _to_24h(mm["ampm"], int(mm["h"])), int(mm["m"]))
                cur = Message(room, mm["sender"].strip(), mm["text"], ts)
                continue

        # 매치 안 된 줄 = 이전 메시지의 연속 줄 (멀티라인)
        if cur is not None:
            cur.text += "\n" + line

    if (m := flush()):
        yield m


def parse_file_meta(path: str | Path) -> tuple[list[Message], datetime | None]:
    """(메시지 리스트, 저장한 날짜). 저장한 날짜가 없으면 파일 mtime."""
    p = Path(path)
    lines = _read_lines(p)
    saved = parse_saved_at(lines) or datetime.fromtimestamp(p.stat().st_mtime)
    msgs = list(parse_lines(lines, room_fallback=p.stem))
    return [m for m in msgs if not any(h in m.text for h in SYSTEM_HINTS)], saved


def _read_lines(p: Path) -> list[str]:
    raw = p.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return raw.decode(enc).splitlines()
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace").splitlines()


def parse_file(path: str | Path) -> list[Message]:
    return parse_file_meta(path)[0]


if __name__ == "__main__":
    import sys
    from collections import Counter
    for f in sys.argv[1:]:
        msgs = parse_file(f)
        print(f"{f}: {len(msgs)} msgs, format={detect_format(Path(f).read_text(encoding='utf-8', errors='ignore').splitlines())}")
        if msgs:
            print("  range:", msgs[0].ts, "~", msgs[-1].ts)
            print("  senders:", Counter(m.sender for m in msgs).most_common(5))
