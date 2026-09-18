"""L1 세션: 6시간 이상 공백을 기준으로 대화를 나눈다. 시작자/종료자가 대칭성·온도의 입력."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from parser import Message

GAP_HOURS = 6


@dataclass
class Session:
    room: str
    start: datetime
    end: datetime
    starter: str
    ender: str
    msgs: list[Message] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.msgs)

    @property
    def duration_min(self) -> float:
        return (self.end - self.start).total_seconds() / 60


def split_sessions(msgs: list[Message], gap_h: float = GAP_HOURS) -> list[Session]:
    """여러 방이 섞여 있어도 됨. 방별로 정렬 후 분할."""
    by_room: dict[str, list[Message]] = defaultdict(list)
    for m in msgs:
        by_room[m.room].append(m)
    out: list[Session] = []
    for room, ms in by_room.items():
        ms.sort(key=lambda x: x.ts)
        cur: list[Message] = []
        for m in ms:
            if cur and (m.ts - cur[-1].ts).total_seconds() > gap_h * 3600:
                out.append(_mk(room, cur))
                cur = []
            cur.append(m)
        if cur:
            out.append(_mk(room, cur))
    out.sort(key=lambda s: s.start)
    return out


def _mk(room: str, ms: list[Message]) -> Session:
    return Session(room, ms[0].ts, ms[-1].ts, ms[0].sender, ms[-1].sender, ms)


def room_participants(msgs: list[Message]) -> dict[str, set[str]]:
    d: dict[str, set[str]] = defaultdict(set)
    for m in msgs:
        d[m.room].add(m.sender)
    return d


def relationship_messages(all_msgs: list[Message], me: str, target: str) -> list[Message]:
    """나와 target 둘만 있는 방(1:1)의 메시지. 없으면 target이 있는 방 전체에서 둘의 메시지만."""
    parts = room_participants(all_msgs)
    one_on_one = {r for r, p in parts.items() if p == {me, target} or p == {target} or p == {me, target}}
    rel = [m for m in all_msgs if m.room in one_on_one]
    if rel:
        return sorted(rel, key=lambda m: m.ts)
    rooms = {r for r, p in parts.items() if target in p}
    return sorted([m for m in all_msgs if m.room in rooms and m.sender in (me, target)], key=lambda m: m.ts)


def other_messages(all_msgs: list[Message], rel_msgs: list[Message]) -> list[Message]:
    rel_rooms = {m.room for m in rel_msgs}
    return [m for m in all_msgs if m.room not in rel_rooms]
