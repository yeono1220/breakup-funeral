"""F5 대칭성 + 나의 편향 + 답장 대기."""
from __future__ import annotations

from datetime import datetime
from statistics import mean

from parser import Message
from core import textfeat as tf
from core.replies import reply_gaps, med, my_overall_reply_median
from core.sessions import split_sessions, other_messages


def _ratio(a: float, b: float) -> float | None:
    if a == 0 and b == 0:
        return None
    return round(a / (a + b), 3)


def symmetry(rel_msgs: list[Message], me: str, target: str) -> dict:
    """나:상대 비율 5개 + 답장 중앙값. share = 나의 몫(0~1), 0.5가 균형."""
    mine = [m for m in rel_msgs if m.sender == me]
    theirs = [m for m in rel_msgs if m.sender == target]
    sessions = split_sessions(rel_msgs)
    starts_me = sum(1 for s in sessions if s.starter == me)
    ends_me = sum(1 for s in sessions if s.ender == me)
    q_me = sum(1 for m in mine if tf.is_question(m.text))
    q_th = sum(1 for m in theirs if tf.is_question(m.text))
    ch_me = sum(m.n_chars for m in mine)
    ch_th = sum(m.n_chars for m in theirs)
    g = reply_gaps(rel_msgs, me).get(target, {"me": [], "them": []})
    return {
        "target": target,
        "n_sessions": len(sessions),
        "bars": [
            {"key": "messages", "label": "메시지 수", "me": len(mine), "them": len(theirs), "share": _ratio(len(mine), len(theirs))},
            {"key": "chars", "label": "글자 수", "me": ch_me, "them": ch_th, "share": _ratio(ch_me, ch_th)},
            {"key": "starts", "label": "먼저 말 걸기", "me": starts_me, "them": len(sessions) - starts_me, "share": _ratio(starts_me, len(sessions) - starts_me)},
            {"key": "ends", "label": "대화 끝내기", "me": ends_me, "them": len(sessions) - ends_me, "share": _ratio(ends_me, len(sessions) - ends_me)},
            {"key": "questions", "label": "질문 수", "me": q_me, "them": q_th, "share": _ratio(q_me, q_th)},
        ],
        "reply": {
            "my_median_min": med(g["me"]), "their_median_min": med(g["them"]),
            "n_my": len(g["me"]), "n_their": len(g["them"]),
        },
    }


def _style_of(msgs: list[Message]) -> dict:
    texts = [m for m in msgs if not m.is_media]
    n = max(1, len(texts))
    return {
        "avg_len": round(mean([m.n_chars for m in texts]), 1) if texts else 0.0,
        "kkk_density": round(sum(tf.kkk_len(m.text) for m in texts) / n, 3),
        "kkk_ratio": round(sum(1 for m in texts if tf.has_kkk(m.text)) / n, 3),
        "emoji_ratio": round(sum(1 for m in texts if tf.has_emoji(m.text)) / n, 3),
        "question_ratio": round(sum(1 for m in texts if tf.is_question(m.text)) / n, 3),
        "late_night_ratio": round(sum(1 for m in msgs if 1 <= m.ts.hour < 5) / max(1, len(msgs)), 3),
        "n": len(msgs),
    }


def _mult(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return round(a / b, 2)


def my_bias(all_msgs: list[Message], rel_msgs: list[Message], me: str, target: str) -> dict:
    """이 상대에게 vs 내 다른 모든 대화(baseline). 배수 > 1 이면 이 상대에게 더 그렇다."""
    others = other_messages(all_msgs, rel_msgs)
    mine_rel = [m for m in rel_msgs if m.sender == me]
    mine_oth = [m for m in others if m.sender == me]
    s_rel, s_oth = _style_of(mine_rel), _style_of(mine_oth)
    g = reply_gaps(rel_msgs, me).get(target, {"me": []})
    my_rel_med = med(g["me"])
    my_oth_med = my_overall_reply_median(others, me)
    speed_mult = _mult(my_oth_med, my_rel_med)   # baseline이 더 느리면 >1 = "이 사람한테 N배 빨리"
    return {
        "target": target,
        "baseline_people": len({m.sender for m in others if m.sender != me}),
        "reply_speed": {"to_target_min": my_rel_med, "to_others_min": my_oth_med, "times_faster": speed_mult},
        "length": {"to_target": s_rel["avg_len"], "to_others": s_oth["avg_len"], "times": _mult(s_rel["avg_len"], s_oth["avg_len"])},
        "kkk": {"to_target": s_rel["kkk_density"], "to_others": s_oth["kkk_density"], "times": _mult(s_rel["kkk_density"], s_oth["kkk_density"])},
        "questions": {"to_target": s_rel["question_ratio"], "to_others": s_oth["question_ratio"], "times": _mult(s_rel["question_ratio"], s_oth["question_ratio"])},
        "late_night": {"with_target": s_rel["late_night_ratio"], "with_others": s_oth["late_night_ratio"]},
        "n_target": s_rel["n"], "n_others": s_oth["n"],
    }


def waiting_reply(rel_msgs: list[Message], me: str, target: str, now: datetime, after_h: float = 3) -> dict | None:
    """상대 마지막 메시지가 열린 메시지이고 after_h 넘게 내가 답 안 했으면 반환."""
    if not rel_msgs:
        return None
    last = rel_msgs[-1]
    if last.sender != target:
        return None
    age_h = (now - last.ts).total_seconds() / 3600
    if age_h < after_h:
        return None
    # 상대가 연속으로 보낸 마지막 묶음 중 하나라도 열려 있으면 열린 것으로
    burst: list[Message] = []
    for m in reversed(rel_msgs):
        if m.sender != target:
            break
        burst.append(m)
    opened = [(m, tf.is_open_message(m.text)) for m in burst]
    hit = next(((m, r) for m, (ok, r) in opened if ok), None)
    if not hit:
        return None
    m, reason = hit
    g = reply_gaps(rel_msgs, me).get(target, {"me": []})
    usual = med(g["me"])
    return {
        "target": target, "msg_id": m.id, "text": m.text[:120], "ts": m.ts.isoformat(),
        "age_hours": round(age_h, 1), "reason": reason,
        "usual_reply_min": usual,
        "times_slower": round(age_h * 60 / usual, 1) if usual else None,
    }
