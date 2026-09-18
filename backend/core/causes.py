"""F3c 사망 원인 진단: '가장 활발했던 4주(전성기)' vs '마지막 활동 4주(말기)'를 비교해 원인 기여도를 배분.
전부 코드 계산. 각 원인에 숫자 근거를 붙인다. 사용자가 알려준 이별 방식(잠수 등)이 있으면 항목으로 반영.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from statistics import median

from parser import Message
from core import textfeat as tf
from core.replies import reply_gaps
from core.sessions import split_sessions

WINDOW_WEEKS = 4


def _fmt_min(m: float | None) -> str:
    if m is None:
        return "–"
    if m < 1:
        return "1분 이내"
    return f"{m:.0f}분" if m < 60 else (f"{m/60:.1f}시간" if m < 1440 else f"{m/1440:.1f}일")


def _metrics(ws: list[Message], me: str, target: str, days: int) -> dict:
    mine = [m for m in ws if m.sender == me]
    theirs = [m for m in ws if m.sender == target]
    th_text = [m for m in theirs if not m.is_media]
    my_text = [m for m in mine if not m.is_media]
    g = reply_gaps(ws, me).get(target, {"me": [], "them": []})
    sessions = split_sessions(ws)
    return {
        "n": len(ws), "per_day": len(ws) / max(1, days),
        "their_med": median(g["them"]) if g["them"] else None,
        "my_med": median(g["me"]) if g["me"] else None,
        "my_start": (sum(1 for s in sessions if s.starter == me) / len(sessions)) if sessions else None,
        "their_len": (sum(m.n_chars for m in th_text) / len(th_text)) if th_text else None,
        "my_len": (sum(m.n_chars for m in my_text) / len(my_text)) if my_text else None,
        "their_q": (sum(1 for m in th_text if tf.is_question(m.text)) / len(th_text)) if th_text else None,
        "their_share": (len(theirs) / len(ws)) if ws else None,
    }


def _log_ratio(a: float | None, b: float | None, floor: float = 0.5) -> float:
    """b→a 로 얼마나 나빠졌나 (log2, 0 이상). floor: 분 단위 최소값(0분 나눗셈 방지)."""
    if a is None or b is None:
        return 0.0
    return max(0.0, math.log2(max(a, floor) / max(b, floor)))


def diagnose(rel: list[Message], me: str, target: str, now: datetime, user_ctx: dict | None = None) -> dict:
    user_ctx = user_ctx or {}
    if len(rel) < 30:
        return {"causes": [], "note": "메시지가 너무 적어 원인 분석 불가", "peak": None, "last": None}

    # ---- 주 단위 버킷
    def wk(d: datetime) -> datetime:
        d0 = d.replace(hour=0, minute=0, second=0, microsecond=0)
        return d0 - timedelta(days=d0.weekday())
    weeks: dict[datetime, list[Message]] = {}
    for m in rel:
        weeks.setdefault(wk(m.ts), []).append(m)
    keys = sorted(weeks)
    start, end = keys[0], keys[-1]
    all_weeks = []
    w = start
    while w <= end:
        all_weeks.append(w); w += timedelta(days=7)

    # 전성기: 연속 4주 메시지 수 최대 구간
    best_i, best_n = 0, -1
    for i in range(0, max(1, len(all_weeks) - WINDOW_WEEKS + 1)):
        n = sum(len(weeks.get(k, [])) for k in all_weeks[i:i + WINDOW_WEEKS])
        if n > best_n:
            best_i, best_n = i, n
    peak_keys = all_weeks[best_i:best_i + WINDOW_WEEKS]
    # 말기: 메시지가 있는 마지막 4주 (전성기와 겹치면 그 뒤 구간이 없다는 뜻)
    active = [k for k in all_weeks if weeks.get(k)]
    last_keys = active[-WINDOW_WEEKS:]
    overlap = len(set(peak_keys) & set(last_keys)) / WINDOW_WEEKS

    peak_ms = [m for k in peak_keys for m in weeks.get(k, [])]
    last_ms = [m for k in last_keys for m in weeks.get(k, [])]
    P = _metrics(peak_ms, me, target, 7 * len(peak_keys))
    L = _metrics(last_ms, me, target, 7 * len(last_keys))

    ending = user_ctx.get("ending")
    # 침묵 기간: 사용자가 '끝났다'고 했으면 내보내기 시점이 아니라 오늘(또는 헤어진 날)까지가 침묵
    ref = now
    if ending in ("ghosted", "dumped", "dumper", "faded", "mutual"):
        ref = max(now, datetime.now())
        if user_ctx.get("ended_at"):
            try:
                ref = max(rel[-1].ts, datetime.fromisoformat(user_ctx["ended_at"]))
            except ValueError:
                pass
    silence_days = max(0.0, (ref - rel[-1].ts).total_seconds() / 86400)

    causes = []
    # 1) 상대 응답 둔화
    v = _log_ratio(L["their_med"], P["their_med"], floor=2.0)   # 2분 미만 차이는 무시
    causes.append({"key": "their_reply", "label": "상대의 읽씹 (응답 둔화)", "raw": v, "weight": 1.2,
                   "evidence": f"상대 답장 중앙값 {_fmt_min(P['their_med'])} → {_fmt_min(L['their_med'])}" + (f" ({(max(L['their_med'],2.0)/max(P['their_med'],2.0)):.1f}배)" if P['their_med'] is not None and L['their_med'] is not None else "")})
    # 2) 내 응답 둔화
    v = _log_ratio(L["my_med"], P["my_med"], floor=2.0)
    causes.append({"key": "my_reply", "label": "나의 응답 둔화", "raw": v, "weight": 0.9,
                   "evidence": f"내 답장 중앙값 {_fmt_min(P['my_med'])} → {_fmt_min(L['my_med'])}"})
    # 3) 대화량 급감
    v = _log_ratio(P["per_day"], L["per_day"], floor=0.2)
    causes.append({"key": "volume", "label": "대화량 급감", "raw": v, "weight": 1.0,
                   "evidence": f"하루 {P['per_day']:.1f}개 → {L['per_day']:.1f}개"})
    # 4) 선톡 편중 (내가 먼저 거는 비율이 말기에 얼마나 치우쳤나)
    ms, ps = L["my_start"], P["my_start"]
    v = 0.0 if ms is None else max(0.0, (ms - 0.5) * 2) + (max(0.0, ms - ps) if ps is not None else 0.0)
    causes.append({"key": "my_start", "label": "유저의 과다 선톡", "raw": v, "weight": 1.0,
                   "evidence": f"내가 먼저 건 비율 {'' if ps is None else f'{ps*100:.0f}% → '}{'' if ms is None else f'{ms*100:.0f}%'}"})
    # 5) 상대 성의 하락 (문장 길이·질문 비율)
    v = _log_ratio(P["their_len"], L["their_len"], floor=1.0) * 0.7 + _log_ratio(P["their_q"], L["their_q"], floor=0.02) * 0.3
    causes.append({"key": "their_effort", "label": "상대의 단답화", "raw": v, "weight": 0.8,
                   "evidence": f"상대 평균 {P['their_len']:.0f}자 → {L['their_len']:.0f}자" if P['their_len'] is not None and L['their_len'] is not None else "표본 부족"})
    # 6) 잠수/침묵 (데이터 밖의 침묵 + 사용자 진술)
    v = min(3.0, silence_days / 7) if silence_days >= 3 else 0.0
    if ending == "ghosted":
        v = max(v, 2.0)
    causes.append({"key": "silence", "label": "잠수 (연락 두절)", "raw": v, "weight": 1.1,
                   "evidence": f"마지막 메시지 후 {silence_days:.0f}일 침묵" + (" · 사용자 진술: 잠수·읽씹" if ending == "ghosted" else "")})

    # ---- 배분
    for c in causes:
        c["score"] = c["raw"] * c["weight"]
    total = sum(c["score"] for c in causes)
    note = None
    if total < 0.15:
        # 데이터상 하락이 거의 없음 → 급사(잠수형) 또는 사용자 진술로 처리
        note = "데이터상 뚜렷한 하락 없이 끝났어요 — 서서히 식은 게 아니라 갑자기 끊긴 모양이에요."
        for c in causes:
            c["score"] = 1.0 if c["key"] == "silence" else 0.0
        total = 1.0
    for c in causes:
        c["pct"] = round(100 * c["score"] / total)
    causes.sort(key=lambda c: -c["pct"])
    # 반올림 보정
    diff = 100 - sum(c["pct"] for c in causes)
    if causes:
        causes[0]["pct"] += diff
    shown = [c for c in causes if c["pct"] > 0][:4]

    return {
        "causes": [{k: c[k] for k in ("key", "label", "pct", "evidence")} for c in shown],
        "note": note,
        "peak": {"from": peak_keys[0].date().isoformat(), "to": (peak_keys[-1] + timedelta(days=6)).date().isoformat(), "n": P["n"], "per_day": round(P["per_day"], 1)},
        "last": {"from": last_keys[0].date().isoformat(), "to": (last_keys[-1] + timedelta(days=6)).date().isoformat(), "n": L["n"], "per_day": round(L["per_day"], 1)},
        "overlap": overlap, "silence_days": round(silence_days),
    }
