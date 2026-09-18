"""F3b 썸 신호 판정: 내 쪽 신호 / 상대 쪽 신호를 baseline 대비로 점수화. 상대 마음이 아니라 '관계 모양'."""
from __future__ import annotations

import math

from parser import Message
from core import textfeat as tf
from core.replies import reply_gaps, med
from core.sessions import split_sessions, other_messages
from core.temperature import r_score

VERDICTS = {
    "mutual": ("서로 신호 있음", "양쪽 다 평소보다 확실히 다르게 굴고 있어. 썸 모양이야."),
    "me_only": ("내 쪽만 뜨거움", "너는 이 사람한테만 다르게 구는데, 상대 쪽 신호는 평소 친구 수준이야."),
    "them_only": ("상대가 더 적극적", "상대 쪽 신호가 세고 너는 평소대로야. 눈치 못 채고 있는 거 아냐?"),
    "friends": ("아직 친구 모양", "양쪽 다 평소 친구들이랑 비슷해. 아직은 친구 모양."),
    "unknown": ("판정 보류", "비교할 1:1 친구 방이 없어서 내 쪽 신호를 못 쟀어. 친구 방 2~3개를 올리면 판정돼."),
}
# 이별 렌즈: 같은 판정을 회고형으로
VERDICTS_RETRO = {
    "mutual": ("서로 신호는 있었어", "양쪽 다 평소와 다르게 굴었어. 마음이 없어서 끝난 관계는 아니었다는 뜻이야."),
    "me_only": ("내 쪽이 더 뜨거웠어", "너는 이 사람한테만 다르게 굴었고, 상대 쪽 신호는 친구 수준이었어. 온도 차가 있던 관계."),
    "them_only": ("상대가 더 적극적이었어", "상대 쪽 신호가 세고 너는 평소대로였어. 상대는 네가 좀 더 적극적이길 바랐을 수도 있어."),
    "friends": ("친구 모양이었어", "양쪽 다 평소 친구들이랑 비슷했어. 애초에 관계의 모양이 연인은 아니었을 수도."),
    "unknown": ("판정 보류", "비교할 1:1 친구 방이 없어서 내 쪽 신호를 못 쟀어. 친구 방 2~3개를 올리면 판정돼."),
}


def retro(result: dict, lens: str) -> dict:
    """렌즈에 맞는 문구로 교체 (breakup이면 회고형)."""
    table = VERDICTS_RETRO if lens == "breakup" else VERDICTS
    title, desc = table.get(result["verdict"], table["friends"])
    return {**result, "title": title, "desc": desc, "retro": lens == "breakup"}


def _log_mult_score(mult: float | None, cap: float = 4.0) -> float | None:
    """배수 → 0..1. 1배=0.5, cap배=1.0, 1/cap배=0.0 (로그)."""
    if mult is None or mult <= 0:
        return None
    return max(0.0, min(1.0, 0.5 + math.log(mult) / (2 * math.log(cap))))


def _ratio_score(x: float | None) -> float | None:
    """0.5 기준 비율 → 0..1 (0.5=0.5, 0.8=1.0)."""
    if x is None:
        return None
    return max(0.0, min(1.0, 0.5 + (x - 0.5) / 0.6))


def _avg(parts: list[tuple[str, float | None, float]]) -> tuple[float | None, list[dict]]:
    """[(label, score, weight)] → (0..100, 사용된 항목)"""
    used = [(l, s, w) for l, s, w in parts if s is not None]
    if not used:
        return None, []
    wsum = sum(w for _, _, w in used)
    total = sum(s * w for _, s, w in used) / wsum
    return round(100 * total), [{"label": l, "score": round(100 * s), "weight": round(w / wsum, 2)} for l, s, w in used]


def signals(all_msgs: list[Message], rel_msgs: list[Message], me: str, target: str) -> dict:
    others = other_messages(all_msgs, rel_msgs)
    mine_rel = [m for m in rel_msgs if m.sender == me and not m.is_media]
    mine_oth = [m for m in others if m.sender == me and not m.is_media]
    them_rel = [m for m in rel_msgs if m.sender == target and not m.is_media]
    them_oth = [m for m in others if m.sender != me and not m.is_media]   # 내 다른 방의 상대들

    def style(ms):
        n = max(1, len(ms))
        return {
            "len": sum(m.n_chars for m in ms) / n,
            "q": sum(1 for m in ms if tf.is_question(m.text)) / n,
            "kkk": sum(tf.kkk_len(m.text) for m in ms) / n,
            "emoji": sum(1 for m in ms if tf.has_emoji(m.text)) / n,
            "late": sum(1 for m in ms if 1 <= m.ts.hour < 5) / n,
        }

    def mult(a, b):
        return None if a is None or b is None or b == 0 else a / b

    s_me_rel, s_me_oth = style(mine_rel), style(mine_oth)
    s_th_rel, s_th_oth = style(them_rel), style(them_oth)

    # ---- 내 쪽
    g_rel = reply_gaps(rel_msgs, me).get(target, {"me": [], "them": []})
    g_oth = reply_gaps(others, me)
    my_med_rel = med(g_rel["me"])
    my_med_oth = med([x for d in g_oth.values() for x in d["me"]])
    speed_mult = mult(my_med_oth, my_med_rel)   # >1 = 이 사람한테 더 빨리
    me_parts = [
        ("답장 속도", _log_mult_score(speed_mult, cap=10), 0.35),
        ("문장 길이", _log_mult_score(mult(s_me_rel["len"], s_me_oth["len"]), cap=2.5), 0.15),
        ("질문 비율", _log_mult_score(mult(s_me_rel["q"], s_me_oth["q"]), cap=2.5), 0.15),
        ("ㅋㅋ·이모지", _log_mult_score(mult(s_me_rel["kkk"] + s_me_rel["emoji"], s_me_oth["kkk"] + s_me_oth["emoji"]), cap=2.5), 0.15),
        ("새벽 대화", _log_mult_score(mult(s_me_rel["late"] + 0.01, s_me_oth["late"] + 0.01), cap=4), 0.20),
    ]
    me_score, me_used = _avg(me_parts)

    # ---- 상대 쪽 (내 다른 방 상대들이 나한테 하는 것 대비)
    their_med = med(g_rel["them"])
    others_to_me_med = med([x for d in g_oth.values() for x in d["them"]])
    sessions = split_sessions(rel_msgs)
    their_start = (sum(1 for s in sessions if s.starter == target) / len(sessions)) if sessions else None
    th_chars = sum(m.n_chars for m in them_rel); my_chars = sum(m.n_chars for m in mine_rel)
    them_parts = [
        ("답장 속도", r_score(their_med) if others_to_me_med is None else _log_mult_score(mult(others_to_me_med, their_med), cap=10), 0.30),
        ("질문 비율", _log_mult_score(mult(s_th_rel["q"], s_th_oth["q"]), cap=2.5), 0.20),
        ("먼저 말 걸기", _ratio_score(their_start), 0.20),
        ("ㅋㅋ·이모지", _log_mult_score(mult(s_th_rel["kkk"] + s_th_rel["emoji"], s_th_oth["kkk"] + s_th_oth["emoji"]), cap=2.5), 0.15),
        ("분량", _ratio_score(th_chars / (th_chars + my_chars)) if th_chars + my_chars else None, 0.15),
    ]
    them_score, them_used = _avg(them_parts)

    # 내 쪽은 baseline(다른 방) 없이는 잴 수 없다 — 항목 2개 미만이면 판정 보류
    if len(me_used) < 2:
        me_score, me_used = None, []
    if me_score is None or them_score is None:
        key = "unknown" if me_score is None else "friends"
    elif me_score >= 55 and them_score >= 55:
        key = "mutual"
    elif me_score >= 55:
        key = "me_only"
    elif them_score >= 55:
        key = "them_only"
    else:
        key = "friends"
    title, desc = VERDICTS[key]

    facts = []
    if speed_mult:
        if speed_mult >= 1:
            facts.append(f"너는 이 사람한테 평소보다 {speed_mult:.1f}배 빨리 답해 ({my_med_rel:.0f}분 vs {my_med_oth:.0f}분)")
        else:
            facts.append(f"너는 이 사람한테 평소보다 {1/speed_mult:.1f}배 느리게 답해 ({my_med_rel:.0f}분 vs {my_med_oth:.0f}분)")
    if their_med is not None and others_to_me_med is not None:
        facts.append(f"상대는 {their_med:.0f}분 안에 답해 (다른 친구들은 너한테 {others_to_me_med:.0f}분)")
    if their_start is not None:
        facts.append(f"대화의 {their_start*100:.0f}%는 상대가 먼저 걸었어")
    if s_th_oth["q"] > 0:
        facts.append(f"상대 질문 비율 {s_th_rel['q']*100:.0f}% (내 다른 친구들 평균 {s_th_oth['q']*100:.0f}%)")

    return {
        "verdict": key, "title": title, "desc": desc,
        "me": {"score": me_score, "parts": me_used},
        "them": {"score": them_score, "parts": them_used},
        "facts": facts[:4],
        "n_baseline_people": len({m.sender for m in others if m.sender != me}),
        "low_confidence": len(rel_msgs) < 200 or len(others) < 100,
        "me_unmeasurable": me_score is None,
    }
