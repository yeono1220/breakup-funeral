"""답장 페어 추출과 요약 통계. stats.py의 _reply_pairs를 대체."""
from __future__ import annotations

from collections import defaultdict
from statistics import median

from parser import Message

REPLY_WINDOW_H = 24


def reply_gaps(msgs: list[Message], me: str) -> dict[str, dict[str, list[float]]]:
    """{person: {"me": [내가 person에게 답한 대기시간(분)...], "them": [person이 나에게 답한...]}}"""
    by_room: dict[str, list[Message]] = defaultdict(list)
    for m in msgs:
        by_room[m.room].append(m)
    out: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"me": [], "them": []})
    for ms in by_room.values():
        ms.sort(key=lambda x: x.ts)
        prev = None
        for m in ms:
            if prev is not None and prev.sender != m.sender:
                gap = (m.ts - prev.ts).total_seconds() / 60
                if gap <= REPLY_WINDOW_H * 60:
                    if m.sender == me:
                        out[prev.sender]["me"].append(gap)
                    elif prev.sender == me:
                        out[m.sender]["them"].append(gap)
            prev = m
    return out


def med(xs: list[float]) -> float | None:
    return round(median(xs), 1) if xs else None


def my_reply_median_to(msgs: list[Message], me: str, person: str) -> float | None:
    return med(reply_gaps(msgs, me).get(person, {}).get("me", []))


def their_reply_median(msgs: list[Message], me: str, person: str) -> float | None:
    return med(reply_gaps(msgs, me).get(person, {}).get("them", []))


def my_overall_reply_median(msgs: list[Message], me: str) -> float | None:
    g = reply_gaps(msgs, me)
    return med([x for d in g.values() for x in d["me"]])
