"""F3 관계 온도 지수 + F4 주간 시계열/업다운 사건. 전부 코드 계산, 가중치 공개."""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean

from parser import Message
from core import textfeat as tf
from core.replies import reply_gaps, med
from core.sessions import split_sessions

# 식음의 증거는 '연락 텀이 길어지고, 답이 짧아지고, 연락이 줄어드는 것'. 이별 대화 주처럼 하루에 메시지가 폭증해도
# 접촉 일수(C)·답장 길이(L)는 안 오르고, 빈도(F)는 하루치를 평시의 2배로 캡해서 한 번의 폭발이 온기로 안 잡히게 한다.
WEIGHTS = {"R": 0.12, "F": 0.15, "C": 0.18, "L": 0.12, "I": 0.06, "V": 0.06, "Q": 0.10, "T": 0.13, "E": 0.08}
LABELS = {"R": "상대 응답성", "F": "대화 빈도", "C": "연락 텀", "L": "상대 답장 길이", "I": "시작 균형", "V": "분량 균형", "Q": "관심 신호", "T": "추세", "E": "감정 어휘"}
BURST_CAP = 2.0   # 하루 메시지 수를 평시의 몇 배까지만 세나
MIN_SESSIONS_FOR_I = 6
MIN_CHARS_FOR_V = 150
MIN_MSGS_PER_WEEK = 5


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def r_score(their_median_min: float | None) -> float | None:
    """5분 이하 1.0, 24시간 이상 0.0, 로그 보간."""
    if their_median_min is None:
        return None
    m = max(their_median_min, 1.0)
    lo, hi = math.log10(5), math.log10(1440)
    return _clamp((hi - math.log10(m)) / (hi - lo))


def f_score(per_day: float, norm_per_day: float | None) -> float | None:
    """관계의 평시 빈도(활발했던 주들의 중앙값) 대비. 같으면 1.0, 1/10이면 0.0 (로그)."""
    if not norm_per_day or norm_per_day <= 0:
        return None
    return _clamp(1 + math.log10(max(per_day, 0.05) / norm_per_day))


def capped_per_day(daily: list[int], days: int, norm_pd: float | None) -> float:
    """하루치를 평시의 BURST_CAP배로 캡한 일평균. 싸움·이별 대화의 폭증을 빈도 상승으로 안 본다."""
    if not daily:
        return 0.0
    cap = norm_pd * BURST_CAP if norm_pd else None
    total = sum(min(c, cap) if cap else c for c in daily)
    return round(total / max(1, days), 2)


def c_score(gap_h: float | None, norm_gap_h: float | None) -> float | None:
    """연락 텀: 대화 세션 사이 공백의 중앙값(시간)을 평시 대비로. 같으면 1.0, 2배면 0.67, 8배면 0.
    하루에 몰아서 400개를 주고받아도 다음 대화까지 이틀 비면 텀은 긴 것 — 폭증이 온기로 안 잡히는 이유."""
    if gap_h is None or not norm_gap_h:
        return None
    return round(_clamp(1 - math.log2(max(gap_h, 0.1) / norm_gap_h) / 3), 3)


def l_score(their_len: float | None, norm_len: float | None) -> float | None:
    """상대 답장 길이: 평시 평균 글자수 대비. 같으면 1.0, 절반이면 0.5, 1/4이면 0."""
    if not their_len or not norm_len:
        return None
    return _clamp(1 + math.log2(their_len / norm_len) / 2)


def i_score(my_start_share: float | None, n_sessions: int = 99) -> float | None:
    if my_start_share is None or n_sessions < MIN_SESSIONS_FOR_I:
        return None
    return _clamp(1 - abs(my_start_share - 0.5) * 2)


def v_score(my_chars: int, their_chars: int) -> float | None:
    if my_chars < MIN_CHARS_FOR_V or their_chars < MIN_CHARS_FOR_V:
        return None
    return _clamp(1 - min(1.0, abs(math.log2(my_chars / their_chars)) / 2))


def q_score(their_q_ratio: float, their_kkk_density: float, base_q: float, base_kkk: float) -> float:
    """baseline 대비. baseline과 같으면 0.5, 2배면 1.0."""
    q = _clamp(their_q_ratio / (2 * max(base_q, 0.03)))
    k = _clamp(their_kkk_density / (2 * max(base_kkk, 0.2)))
    return round((q + k) / 2, 3)


def t_score(cur: dict, prev: dict, norm_pd: float | None = None) -> float | None:
    """추세: 캡한 빈도·접촉 일수·상대 답장 길이가 이전 창보다 올랐나, 상대 답장이 빨라졌나. 각 -1~1을 평균해 0~1로."""
    if not prev or prev.get("per_day", 0) == 0:
        return None
    cpd_cur = capped_per_day(cur.get("daily", []), cur.get("days", 7), norm_pd) or cur["per_day"]
    cpd_prev = capped_per_day(prev.get("daily", []), prev.get("days", 7), norm_pd) or prev["per_day"]
    parts = [_clamp((cpd_cur - cpd_prev) / max(cpd_prev, 0.1), -1, 1)]
    if prev.get("gap_h") and cur.get("gap_h"):
        parts.append(_clamp(-(cur["gap_h"] - prev["gap_h"]) / prev["gap_h"], -1, 1))   # 텀이 길어지면 하락
    if cur.get("their_len") and prev.get("their_len"):
        parts.append(_clamp((cur["their_len"] - prev["their_len"]) / prev["their_len"], -1, 1))
    if cur.get("their_med") and prev.get("their_med"):
        parts.append(_clamp(-(cur["their_med"] - prev["their_med"]) / prev["their_med"], -1, 1))
    return round((mean(parts) + 1) / 2, 3)


def e_score(mood: float | None) -> float | None:
    return None if mood is None else _clamp((mood + 2) / 4)


def baseline_q(others: list[Message], me: str) -> tuple[float, float]:
    """내 다른 방 상대들의 질문 비율·ㅋㅋ 밀도 평균."""
    texts = [m for m in others if m.sender != me and not m.is_media]
    if not texts:
        return 0.15, 0.6
    q = sum(1 for m in texts if tf.is_question(m.text)) / len(texts)
    k = sum(tf.kkk_len(m.text) for m in texts) / len(texts)
    return round(q, 3), round(k, 3)


def window_metrics(ws: list[Message], me: str, target: str, days: int | None = None) -> dict:
    """days: 창 길이(일). 주간=7, 14일 창=14. None이면 메시지 범위로 추정."""
    mine = [m for m in ws if m.sender == me]
    theirs = [m for m in ws if m.sender == target]
    sessions = split_sessions(ws)
    if days is None:
        days = max(1, (ws[-1].ts.date() - ws[0].ts.date()).days + 1) if ws else 1
    g = reply_gaps(ws, me).get(target, {"me": [], "them": []})
    th_text = [m for m in theirs if not m.is_media]
    day_counts: dict = defaultdict(int)
    for m in ws:
        day_counts[m.ts.date()] += 1
    dates = sorted(day_counts)
    max_gap = max(((b - a).days for a, b in zip(dates, dates[1:])), default=0)
    # 세션 사이 공백(시간). 세션이 하나뿐이면 창 전체가 공백인 셈
    gaps = [(b.start - a.end).total_seconds() / 3600 for a, b in zip(sessions, sessions[1:])]
    gap_h = med(gaps) if gaps else (days * 24.0 if ws else None)
    return {
        "n": len(ws), "per_day": round(len(ws) / days, 2), "n_sessions": len(sessions), "days": days,
        "daily": list(day_counts.values()), "active_share": round(len(dates) / max(1, days), 3), "max_gap_days": max_gap,
        "gap_h": round(gap_h, 2) if gap_h is not None else None,
        "their_len": round(mean(m.n_chars for m in th_text), 1) if th_text else None,
        "their_med": med(g["them"]), "my_med": med(g["me"]),
        "my_start_share": (sum(1 for s in sessions if s.starter == me) / len(sessions)) if sessions else None,
        "my_chars": sum(m.n_chars for m in mine), "their_chars": sum(m.n_chars for m in theirs),
        "their_q_ratio": (sum(1 for m in th_text if tf.is_question(m.text)) / len(th_text)) if th_text else 0.0,
        "their_kkk_density": (sum(tf.kkk_len(m.text) for m in th_text) / len(th_text)) if th_text else 0.0,
        "greetings": sum(1 for m in ws if tf.is_greeting(m.text)),
        "late_ratio": (sum(1 for m in mine if 1 <= m.ts.hour < 5) / len(mine)) if mine else 0.0,
    }


def _top_half_median(vals: list[float]) -> float | None:
    vals = sorted(v for v in vals if v)
    if not vals:
        return None
    top = vals[len(vals) // 2:]
    return round(top[len(top) // 2], 2)


def norm_per_day(rel_msgs: list[Message]) -> float | None:
    """관계의 '평시' 빈도: 주별 메시지/일 중 상위 절반의 중앙값."""
    by_week: dict[datetime, int] = defaultdict(int)
    for m in rel_msgs:
        by_week[_week_start(m.ts)] += 1
    return _top_half_median([v / 7 for v in by_week.values()])


def norms(rel_msgs: list[Message], target: str) -> dict:
    """평시 기준 3종: 빈도(메시지/일), 접촉 일수 비율, 상대 평균 글자수 — 활발했던 주(상위 절반)의 중앙값."""
    by_week: dict[datetime, list[Message]] = defaultdict(list)
    for m in rel_msgs:
        by_week[_week_start(m.ts)].append(m)
    weeks = list(by_week.values())
    active = [len({m.ts.date() for m in ws}) / 7 for ws in weeks]
    gaps = []
    for ws in weeks:
        ss = split_sessions(ws)
        g = [(b.start - a.end).total_seconds() / 3600 for a, b in zip(ss, ss[1:])]
        if len(g) >= 2:
            gaps.append(med(g))
    gaps = sorted(gaps)
    norm_gap = (gaps[: max(1, len(gaps) // 2)] or [None])   # 텀이 짧았던 절반
    norm_gap = norm_gap[len(norm_gap) // 2] if norm_gap and norm_gap[0] is not None else None
    lens = []
    for ws in weeks:
        th = [m.n_chars for m in ws if m.sender == target and not m.is_media]
        if len(th) >= 5:
            lens.append(mean(th))
    return {"per_day": norm_per_day(rel_msgs), "active_share": _top_half_median(active), "their_len": _top_half_median(lens),
            "gap_h": round(norm_gap, 2) if norm_gap else None}


def compose(cur: dict, prev: dict | None, base: tuple[float, float], mood: float | None = None,
            norm: dict | float | None = None) -> dict:
    if not isinstance(norm, dict):   # 구버전 호출(빈도만)
        norm = {"per_day": norm, "active_share": None, "their_len": None}
    npd = norm.get("per_day")
    comps = {
        "R": r_score(cur["their_med"]),
        "F": f_score(capped_per_day(cur.get("daily", []), cur.get("days", 7), npd) or cur["per_day"], npd),
        "C": c_score(cur.get("gap_h"), norm.get("gap_h")),
        "L": l_score(cur.get("their_len"), norm.get("their_len")),
        "I": i_score(cur["my_start_share"], cur.get("n_sessions", 99)) if cur["n"] >= 30 else None,
        "V": v_score(cur["my_chars"], cur["their_chars"]) if cur["n"] >= 30 else None,
        "Q": q_score(cur["their_q_ratio"], cur["their_kkk_density"], *base),
        "T": t_score(cur, prev, npd) if prev else None,
        "E": e_score(mood),
    }
    avail = {k: v for k, v in comps.items() if v is not None}
    if not avail:
        return {"temp": None, "components": {}}
    wsum = sum(WEIGHTS[k] for k in avail)
    detail = {k: {"label": LABELS[k], "value": round(v, 3), "weight": round(WEIGHTS[k] / wsum, 3),
                  "contrib": round(100 * v * WEIGHTS[k] / wsum, 1)} for k, v in avail.items()}
    temp = round(sum(d["contrib"] for d in detail.values()), 1)
    return {"temp": temp, "components": detail}


def temperature_now(rel_msgs: list[Message], me: str, target: str, base: tuple[float, float],
                    now: datetime | None = None, mood: float | None = None) -> dict:
    """현재 온도: 최근 14일 창, 추세는 이전 28일 대비. 지난주 대비 Δ 포함."""
    if not rel_msgs:
        return {"temp": None}
    now = now or rel_msgs[-1].ts
    cur_w = [m for m in rel_msgs if m.ts > now - timedelta(days=14)]
    prev_w = [m for m in rel_msgs if now - timedelta(days=42) < m.ts <= now - timedelta(days=14)]
    last_w = [m for m in rel_msgs if now - timedelta(days=21) < m.ts <= now - timedelta(days=7)]
    last_prev = [m for m in rel_msgs if now - timedelta(days=49) < m.ts <= now - timedelta(days=21)]
    nm = norms(rel_msgs, target); npd = nm["per_day"]
    cur = compose(window_metrics(cur_w, me, target, 14), window_metrics(prev_w, me, target, 28) if prev_w else None, base, mood, nm) \
        if len(cur_w) >= MIN_MSGS_PER_WEEK else {"temp": None, "components": {}}
    last = compose(window_metrics(last_w, me, target, 14), window_metrics(last_prev, me, target, 28) if last_prev else None, base, mood, nm) \
        if len(last_w) >= MIN_MSGS_PER_WEEK else {"temp": None, "components": {}}
    delta = round(cur["temp"] - last["temp"], 1) if cur["temp"] is not None and last["temp"] is not None else None
    return {
        "temp": cur["temp"], "delta_week": delta, "components": cur["components"],
        "top_factor": top_factor(last["components"], cur["components"]),
        "window": [ (now - timedelta(days=14)).date().isoformat(), now.date().isoformat() ],
        "n_window": len(cur_w), "sparse": len(cur_w) < 30, "norm_per_day": npd,
        "weights": WEIGHTS,
    }


def top_factor(prev_c: dict, cur_c: dict) -> dict | None:
    keys = set(prev_c) & set(cur_c)
    if not keys:
        return None
    k = max(keys, key=lambda x: abs(cur_c[x]["contrib"] - prev_c[x]["contrib"]))
    d = round(cur_c[k]["contrib"] - prev_c[k]["contrib"], 1)
    return {"key": k, "label": LABELS[k], "delta_contrib": d, "direction": "up" if d > 0 else "down"}


def _week_start(d: datetime) -> datetime:
    d0 = d.replace(hour=0, minute=0, second=0, microsecond=0)
    return d0 - timedelta(days=d0.weekday())


def weekly_series(rel_msgs: list[Message], me: str, target: str, base: tuple[float, float],
                  moods: dict[str, float] | None = None) -> list[dict]:
    """주별 온도·지표. 데이터 없는 주도 채움(temp=None)."""
    if not rel_msgs:
        return []
    by_week: dict[datetime, list[Message]] = defaultdict(list)
    for m in rel_msgs:
        by_week[_week_start(m.ts)].append(m)
    start, end = _week_start(rel_msgs[0].ts), _week_start(rel_msgs[-1].ts)
    nm = norms(rel_msgs, target)
    weeks = []
    w = start
    while w <= end:
        weeks.append(w)
        w += timedelta(days=7)
    out = []
    for i, w in enumerate(weeks):
        ws = by_week.get(w, [])
        prev_ms = [m for k in weeks[max(0, i - 4):i] for m in by_week.get(k, [])]
        met = window_metrics(ws, me, target, 7) if ws else {"n": 0, "per_day": 0.0, "n_sessions": 0, "days": 7, "daily": [], "active_share": 0.0, "max_gap_days": 0, "gap_h": None,
                                                          "their_len": None, "their_med": None, "my_med": None,
                                                          "my_start_share": None, "my_chars": 0, "their_chars": 0,
                                                          "their_q_ratio": 0.0, "their_kkk_density": 0.0, "greetings": 0, "late_ratio": 0.0}
        mood = (moods or {}).get(w.date().isoformat())
        comp = compose(met, window_metrics(prev_ms, me, target, 7 * min(4, i)) if prev_ms else None, base, mood, nm) \
            if len(ws) >= MIN_MSGS_PER_WEEK else {"temp": None, "components": {}}
        out.append({"week_start": w.date().isoformat(), "temp": comp["temp"], "temp_raw": comp["temp"], "components": comp["components"],
                    "n": met["n"], "per_day": met["per_day"], "their_med": met["their_med"], "my_med": met["my_med"],
                    "my_start_share": None if met["my_start_share"] is None else round(met["my_start_share"], 2),
                    "greetings": met["greetings"], "late_ratio": round(met["late_ratio"], 2)})
    # 3주 평활(0.5/0.3/0.2): 이별 대화처럼 한 주만 폭증해도 "다시 뜨거워졌다"로 안 읽히게. 원값은 temp_raw에.
    hist: list[float] = []
    for row in out:
        if row["temp_raw"] is None:
            continue
        ws_ = [0.5, 0.3, 0.2][: 1 + len(hist)]
        vals = [row["temp_raw"]] + hist[::-1]
        row["temp"] = round(sum(v * w_ for v, w_ in zip(vals, ws_)) / sum(ws_), 1)
        hist = (hist + [row["temp_raw"]])[-2:]
    return out


MIN_MSGS_FOR_EVENT = 20


def updown_events(series: list[dict], rel_msgs: list[Message], target: str, min_delta: float = 8.0) -> list[dict]:
    """온도 시계열의 굵직한 업다운. 각 사건에 주요인 + 그 주의 근거 후보 msg_id.
    표본이 적은 주(메시지 < MIN_MSGS_FOR_EVENT)는 노이즈라 사건으로 안 침."""
    by_week: dict[str, list[Message]] = defaultdict(list)
    for m in rel_msgs:
        by_week[_week_start(m.ts).date().isoformat()].append(m)
    events, prev = [], None
    for row in series:
        if row["temp"] is None:
            continue
        if prev is not None and row["n"] >= MIN_MSGS_FOR_EVENT and prev["n"] >= MIN_MSGS_FOR_EVENT:
            d = round(row["temp"] - prev["temp"], 1)
            if abs(d) >= min_delta:
                ws = by_week.get(row["week_start"], [])
                ev = [m for m in ws if not m.is_media and tf.has_emotion(m.text)]
                ev = ev or sorted([m for m in ws if not m.is_media], key=lambda m: -m.n_chars)[:3]
                events.append({
                    "week_start": row["week_start"], "temp": row["temp"], "delta": d,
                    "direction": "up" if d > 0 else "down",
                    "top_factor": top_factor(prev["components"], row["components"]),
                    "evidence_ids": [m.id for m in ev[:3] if m.id is not None],
                    "evidence_preview": [{"id": m.id, "sender": m.sender, "text": m.text[:60], "ts": m.ts.isoformat()} for m in ev[:3]],
                    "title": None,  # 에피소드 카드가 채움
                })
        prev = row
    return events
