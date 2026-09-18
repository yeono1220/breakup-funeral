"""메시지 리스트 → 대시보드/코치용 통계. 전부 순수 함수.

`me` = 내 이름(카톡 export에 찍히는 표시명).
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import median

from parser import Message
from core.textfeat import is_open_message

REPLY_WINDOW_H = 24          # 이 시간 넘게 지나 온 메시지는 "답장"으로 안 침 (새 대화 시작)
UNANSWERED_AFTER_H = 3       # 상대 마지막 메시지 후 이 시간 지나면 미답장
WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]

_RE_KKK = re.compile(r"ㅋ{2,}")
_RE_YY = re.compile(r"ㅠ{2,}|ㅜ{2,}")
_RE_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
_RE_URL = re.compile(r"https?://\S+")
_RE_WORD = re.compile(r"[가-힣a-zA-Z]{2,}")
_STOP = set("그리고 그래서 근데 그냥 진짜 이거 저거 그거 우리 내가 너가 니가 나도 너도 하는 있는 없는 그런 이런 저런 오늘 내일 지금 이제 아니 아냐 아닌 ㅇㅇ ㄴㄴ ㅇㅋ 사진 이모티콘 동영상".split())


# ---------------------------------------------------------------- overview
def overview(msgs: list[Message], me: str) -> dict:
    if not msgs:
        return {"total": 0}
    mine = [m for m in msgs if m.sender == me]
    rooms = Counter(m.room for m in msgs)
    people = Counter(m.sender for m in msgs if m.sender != me)
    return {
        "total": len(msgs),
        "mine": len(mine),
        "my_ratio": round(len(mine) / len(msgs), 3),
        "first_ts": msgs[0].ts.isoformat(),
        "last_ts": msgs[-1].ts.isoformat(),
        "days": (msgs[-1].ts - msgs[0].ts).days + 1,
        "rooms": len(rooms),
        "people": len(people),
        "top_rooms": rooms.most_common(5),
        "top_people": people.most_common(5),
    }


# ---------------------------------------------------------------- activity
def activity_heatmap(msgs: list[Message], me: str, only_me: bool = True) -> list[list[int]]:
    """[weekday 0..6][hour 0..23] 메시지 수."""
    grid = [[0] * 24 for _ in range(7)]
    for m in msgs:
        if only_me and m.sender != me:
            continue
        grid[m.ts.weekday()][m.ts.hour] += 1
    return grid


def activity_by_hour(msgs: list[Message], me: str) -> list[int]:
    h = [0] * 24
    for m in msgs:
        if m.sender == me:
            h[m.ts.hour] += 1
    return h


def late_night_ratio(msgs: list[Message], me: str, start=1, end=5) -> float:
    mine = [m for m in msgs if m.sender == me]
    if not mine:
        return 0.0
    late = sum(1 for m in mine if start <= m.ts.hour < end)
    return round(late / len(mine), 3)


# ---------------------------------------------------------------- reply
def _reply_pairs(msgs: list[Message], me: str):
    """방별로 정렬된 메시지에서 (상대 → 나) / (나 → 상대) 전환 지점의 대기시간(분)을 뽑는다."""
    by_room: dict[str, list[Message]] = defaultdict(list)
    for m in msgs:
        by_room[m.room].append(m)
    for room, ms in by_room.items():
        ms.sort(key=lambda x: x.ts)
        prev = None
        for m in ms:
            if prev is not None and prev.sender != m.sender:
                gap = (m.ts - prev.ts).total_seconds() / 60
                if gap <= REPLY_WINDOW_H * 60:
                    if m.sender == me:
                        yield ("me", room, prev.sender, gap)          # 내가 prev.sender에게 답
                    elif prev.sender == me:
                        yield ("them", room, m.sender, gap)           # m.sender가 나에게 답
            prev = m


def reply_stats(msgs: list[Message], me: str) -> list[dict]:
    """사람별: 내 답장 중앙값/평균, 상대 답장 중앙값, 표본 수. 1:1 방 기준이 가장 정확."""
    mine: dict[str, list[float]] = defaultdict(list)
    theirs: dict[str, list[float]] = defaultdict(list)
    for who, room, person, gap in _reply_pairs(msgs, me):
        (mine if who == "me" else theirs)[person].append(gap)
    out = []
    for person in set(mine) | set(theirs):
        a, b = mine.get(person, []), theirs.get(person, [])
        if len(a) + len(b) < 5:
            continue
        out.append({
            "person": person,
            "my_median_min": round(median(a), 1) if a else None,
            "my_mean_min": round(sum(a) / len(a), 1) if a else None,
            "their_median_min": round(median(b), 1) if b else None,
            "n_my_replies": len(a),
            "n_their_replies": len(b),
        })
    out.sort(key=lambda d: -(d["n_my_replies"] + d["n_their_replies"]))
    return out


def reply_trend(msgs: list[Message], me: str, weeks: int = 8) -> list[dict]:
    """최근 N주 주별 내 답장 중앙값(분)."""
    if not msgs:
        return []
    end = max(m.ts for m in msgs)
    buckets: dict[int, list[float]] = defaultdict(list)
    pairs = list(_reply_pairs(msgs, me))
    # 주 인덱스 계산을 위해 원본 ts가 필요하므로 다시 순회
    by_room: dict[str, list[Message]] = defaultdict(list)
    for m in msgs:
        by_room[m.room].append(m)
    for ms in by_room.values():
        ms.sort(key=lambda x: x.ts)
        prev = None
        for m in ms:
            if prev is not None and prev.sender != me and m.sender == me:
                gap = (m.ts - prev.ts).total_seconds() / 60
                if gap <= REPLY_WINDOW_H * 60:
                    w = (end - m.ts).days // 7
                    if w < weeks:
                        buckets[w].append(gap)
            prev = m
    return [{"weeks_ago": w, "my_median_min": round(median(buckets[w]), 1) if buckets.get(w) else None,
             "n": len(buckets.get(w, []))} for w in range(weeks - 1, -1, -1)]


def unanswered(msgs: list[Message], me: str, now: datetime | None = None, after_h: int = UNANSWERED_AFTER_H) -> list[dict]:
    """상대가 마지막으로 말했고 내가 after_h 시간 넘게 답 안 한 방."""
    now = now or max((m.ts for m in msgs), default=datetime.now())
    last: dict[str, Message] = {}
    for m in msgs:
        if m.room not in last or m.ts > last[m.room].ts:
            last[m.room] = m
    out = []
    for room, m in last.items():
        if m.sender != me:
            age_h = (now - m.ts).total_seconds() / 3600
            is_open, reason = is_open_message(m.text)
            if age_h >= after_h and is_open:
                out.append({"room": room, "sender": m.sender, "text": m.text[:80], "ts": m.ts.isoformat(),
                            "age_hours": round(age_h, 1), "reason": reason})
    out.sort(key=lambda d: d["age_hours"])
    return out


# ---------------------------------------------------------------- style
def my_style(msgs: list[Message], me: str) -> dict:
    mine = [m for m in msgs if m.sender == me]
    if not mine:
        return {"n": 0}
    texts = [m.text for m in mine]
    n = len(texts)
    words = Counter()
    for t in texts:
        t = _RE_URL.sub("", t)
        for w in _RE_WORD.findall(t):
            if w not in _STOP:
                words[w] += 1
    lengths = [len(t) for t in texts]
    return {
        "n": n,
        "avg_len": round(sum(lengths) / n, 1),
        "median_len": median(lengths),
        "kkk_count": sum(len(_RE_KKK.findall(t)) for t in texts),
        "kkk_ratio": round(sum(1 for t in texts if _RE_KKK.search(t)) / n, 3),
        "yy_count": sum(len(_RE_YY.findall(t)) for t in texts),
        "question_ratio": round(sum(1 for t in texts if "?" in t) / n, 3),
        "exclaim_ratio": round(sum(1 for t in texts if "!" in t) / n, 3),
        "emoji_ratio": round(sum(1 for t in texts if _RE_EMOJI.search(t)) / n, 3),
        "photo_count": sum(1 for t in texts if t.strip() in ("사진", "이모티콘", "동영상")),
        "top_words": words.most_common(20),
        "late_night_ratio": late_night_ratio(msgs, me),
    }


def style_examples(msgs: list[Message], me: str, person: str | None = None, k: int = 30) -> list[str]:
    """답장 초안용: 내가 (특정 상대에게) 보낸 최근 메시지 샘플."""
    mine = [m for m in msgs if m.sender == me and len(m.text) > 3 and m.text.strip() not in ("사진", "이모티콘")]
    if person:
        rooms = {m.room for m in msgs if m.sender == person}
        mine = [m for m in mine if m.room in rooms]
    return [m.text for m in mine[-k:]]


# ---------------------------------------------------------------- weekly report
def weekly_report(msgs: list[Message], me: str) -> dict:
    """최근 7일 vs 그 전 7일 비교 카드."""
    if not msgs:
        return {}
    end = max(m.ts for m in msgs)
    this_start, prev_start = end - timedelta(days=7), end - timedelta(days=14)
    this = [m for m in msgs if m.ts > this_start]
    prev = [m for m in msgs if prev_start < m.ts <= this_start]

    def summary(ms):
        mine = [m for m in ms if m.sender == me]
        people = Counter(m.sender for m in ms if m.sender != me)
        return {
            "total": len(ms), "mine": len(mine),
            "top_person": people.most_common(1)[0] if people else None,
            "kkk": sum(len(_RE_KKK.findall(m.text)) for m in mine),
            "late_night": sum(1 for m in mine if 1 <= m.ts.hour < 5),
        }

    a, b = summary(this), summary(prev)
    rs = reply_stats(this, me)
    slowest = max(rs, key=lambda d: d["my_median_min"] or 0) if rs else None
    return {
        "period": [this_start.date().isoformat(), end.date().isoformat()],
        "this": a, "prev": b,
        "delta_total": a["total"] - b["total"],
        "delta_mine": a["mine"] - b["mine"],
        "slowest_reply": slowest,
        "unanswered": unanswered(msgs, me, now=end)[:5],
    }
