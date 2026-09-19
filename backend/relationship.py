"""관계 뷰 조립: core 모듈들을 한 번에 호출해 /relationship 응답을 만든다. 코치 툴도 이걸 재사용."""
from __future__ import annotations

from datetime import datetime

from parser import Message
from core.sessions import relationship_messages, other_messages, room_participants
from core.symmetry import symmetry, my_bias, waiting_reply
from core.temperature import baseline_q, temperature_now, weekly_series, updown_events, WEIGHTS, LABELS
from core.stages import detect_stages
from core.signals import signals


def candidates(all_msgs: list[Message], me: str) -> list[dict]:
    """상대 후보: 1:1 방 우선, 메시지 수 순."""
    parts = room_participants(all_msgs)
    counts: dict[str, int] = {}
    one: dict[str, bool] = {}
    for room, people in parts.items():
        others = people - {me}
        n = sum(1 for m in all_msgs if m.room == room)
        if len(others) == 1:
            p = next(iter(others))
            counts[p] = counts.get(p, 0) + n
            one[p] = True
        else:
            for p in others:
                counts[p] = counts.get(p, 0) + n
                one.setdefault(p, False)
    out = [{"name": p, "messages": n, "one_on_one": one[p]} for p, n in counts.items()]
    out.sort(key=lambda d: (not d["one_on_one"], -d["messages"]))
    return out


def build(all_msgs: list[Message], me: str, target: str, now: datetime, moods: dict[str, float] | None = None,
          started_at: datetime | None = None) -> dict:
    rel = relationship_messages(all_msgs, me, target)
    if not rel:
        return {"target": target, "error": "no messages with target"}
    oth = other_messages(all_msgs, rel)
    base = baseline_q(oth, me)
    series = weekly_series(rel, me, target, base, moods, started_at=started_at)
    temp_now = temperature_now(rel, me, target, base, now=now, started_at=started_at)
    # 화면에 보이는 '지금 온도'는 차트의 마지막 점(3주 평활)과 같은 숫자여야 한다. 14일 창 원값은 temp_window에.
    valid = [w for w in series if w["temp"] is not None]
    if valid:
        temp_now["temp_window"] = temp_now.get("temp")
        temp_now["temp"] = valid[-1]["temp"]
        temp_now["delta_week"] = round(valid[-1]["temp"] - valid[-2]["temp"], 1) if len(valid) >= 2 else None
    return {
        "me": me, "target": target,
        "n_messages": len(rel),
        "range": [rel[0].ts.isoformat(), rel[-1].ts.isoformat()],
        "temperature": temp_now,
        "weekly": series,
        "events": updown_events(series, rel, target),
        "stages": detect_stages(series),
        "symmetry": symmetry(rel, me, target),
        "bias": my_bias(all_msgs, rel, me, target),
        "waiting": waiting_reply(rel, me, target, now),
        "signals": signals(all_msgs, rel, me, target),
        "last_message": {"id": rel[-1].id, "sender": rel[-1].sender, "text": rel[-1].text, "ts": rel[-1].ts.isoformat()},
        "meta": {"weights": WEIGHTS, "labels": LABELS, "baseline_q": base, "now": now.isoformat()},
    }


def parse_date(s: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(s) if s else None
    except ValueError:
        return None


def compare(all_msgs: list[Message], me: str, a: str, b: str, now: datetime) -> dict:
    out = {}
    for p in (a, b):
        rel = relationship_messages(all_msgs, me, p)
        if not rel:
            out[p] = None
            continue
        base = baseline_q(other_messages(all_msgs, rel), me)
        t = temperature_now(rel, me, p, base, now=now)
        s = symmetry(rel, me, p)
        bi = my_bias(all_msgs, rel, me, p)
        out[p] = {
            "n_messages": len(rel), "temp": t["temp"],
            "my_reply_min": s["reply"]["my_median_min"], "their_reply_min": s["reply"]["their_median_min"],
            "my_start_share": next((x["share"] for x in s["bars"] if x["key"] == "starts"), None),
            "my_chars_share": next((x["share"] for x in s["bars"] if x["key"] == "chars"), None),
            "my_avg_len": bi["length"]["to_target"], "my_kkk": bi["kkk"]["to_target"],
            "late_night": bi["late_night"]["with_target"],
        }
    return {"me": me, "a": a, "b": b, "rows": out}
