"""F4.2 단계 자동 감지: 주간 시계열 → 썸/연애/일상/식음/단절 세그먼트 (규칙 기반)."""
from __future__ import annotations

from statistics import mean

STAGE_LABELS = {"some": "썸", "dating": "연애", "steady": "일상", "cooling": "식음", "cutoff": "단절", "gap": "공백"}


def _avg(xs):
    xs = [x for x in xs if x is not None]
    return mean(xs) if xs else None


def classify_weeks(series: list[dict]) -> list[dict]:
    """각 주에 stage + 규칙 히트 수 기반 confidence."""
    out = []
    active = sorted(w["per_day"] for w in series if w["n"] > 0)
    norm_pd = active[len(active) // 2] if active else 0.0   # 관계 평시 빈도(중앙값)
    for i, w in enumerate(series):
        prev = series[max(0, i - 4):i]
        prev_pd = _avg([p["per_day"] for p in prev if p["n"] > 0])
        prev_med = _avg([p["their_med"] for p in prev])
        pd, med, share, greet = w["per_day"], w["their_med"], w["my_start_share"], w["greetings"]

        if w["n"] == 0:
            stage, conf = ("cutoff" if norm_pd >= 3 and i > 0 else "gap"), 0.6
            out.append({**w, "stage": stage, "confidence": conf}); continue
        # 저볼륨 관계(평시 3건/일 미만)는 썸/식음 신호가 노이즈 → 일상으로 고정
        if norm_pd < 3:
            out.append({**w, "stage": "steady", "confidence": 0.5}); continue

        hits = {"some": 0, "dating": 0, "cooling": 0, "cutoff": 0}
        # 연애: 고빈도 안정 + 인사 어휘
        if pd >= 25: hits["dating"] += 1
        if greet >= 10: hits["dating"] += 1
        if pd >= 15 and greet >= 6: hits["dating"] += 1
        # 썸: 응답 빠름(필수) + (빈도 상승 | 시작 균형 | 충분한 빈도)
        if med is not None and med <= 30:
            hits["some"] += 1
            if prev_pd and pd >= prev_pd * 1.15: hits["some"] += 1
            if share is not None and 0.35 <= share <= 0.65: hits["some"] += 1
            if 4 <= pd < 25 and greet < 10: hits["some"] += 1
            if hits["some"] == 1: hits["some"] = 0   # 응답만 빠르고 다른 신호 없으면 일상
        # 식음: 빈도 하락 + 응답 둔화 + 시작 편중
        if prev_pd and pd <= prev_pd * 0.7: hits["cooling"] += 1
        if med is not None and prev_med and med >= prev_med * 2: hits["cooling"] += 1
        if share is not None and share >= 0.7: hits["cooling"] += 1
        # 단절: 매우 저빈도 + 이전엔 활발 (관계 첫 주는 단절일 수 없음)
        had_active_before = any(p["n"] >= 5 for p in series[:i])
        if had_active_before and pd <= max(1.5, norm_pd * 0.15) and norm_pd >= 4: hits["cutoff"] += 2
        if med is not None and med >= 300: hits["cutoff"] += 1

        stage = max(hits, key=hits.get)
        top = hits[stage]
        if top == 0:
            stage, conf = "steady", 0.4
        else:
            conf = round(min(1.0, 0.4 + 0.2 * top), 2)
            # 동점이면 우선순위: cutoff > cooling > dating > some
            for pref in ("cutoff", "cooling", "dating", "some"):
                if hits[pref] == top:
                    stage = pref; break
        out.append({**w, "stage": stage, "confidence": conf})
    return out


def smooth(weeks: list[dict], min_len: int = 2) -> list[dict]:
    """길이 1짜리 세그먼트는 이웃에 흡수."""
    if not weeks:
        return weeks
    st = [w["stage"] for w in weeks]
    changed = True
    while changed:
        changed = False
        i = 0
        while i < len(st):
            j = i
            while j + 1 < len(st) and st[j + 1] == st[i]:
                j += 1
            run = j - i + 1
            if run < min_len and st[i] not in ("cutoff",):
                left = st[i - 1] if i > 0 else None
                right = st[j + 1] if j + 1 < len(st) else None
                repl = left or right
                if repl and repl != st[i]:
                    for k in range(i, j + 1):
                        st[k] = repl
                    changed = True
            i = j + 1
    return [{**w, "stage": s} for w, s in zip(weeks, st)]


def segments(weeks: list[dict]) -> list[dict]:
    segs = []
    for w in weeks:
        if segs and segs[-1]["stage"] == w["stage"]:
            segs[-1]["end"] = w["week_start"]; segs[-1]["weeks"] += 1
            segs[-1]["confidences"].append(w["confidence"])
        else:
            segs.append({"stage": w["stage"], "label": STAGE_LABELS[w["stage"]], "start": w["week_start"],
                         "end": w["week_start"], "weeks": 1, "confidences": [w["confidence"]]})
    for s in segs:
        s["confidence"] = round(mean(s.pop("confidences")), 2)
    return segs


def detect_stages(series: list[dict]) -> dict:
    weeks = smooth(classify_weeks(series))
    segs = segments(weeks)
    current = segs[-1]["stage"] if segs else "steady"
    # 렌즈 매핑: 썸/연애중/이별
    lens = "some" if current == "some" else ("breakup" if current in ("cutoff",) else "dating")
    return {"weeks": [{"week_start": w["week_start"], "stage": w["stage"], "confidence": w["confidence"]} for w in weeks],
            "segments": segs, "current_stage": current, "current_label": STAGE_LABELS[current], "lens": lens}
