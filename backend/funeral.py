"""장례식 전용 LLM 기능: X 소환술(상대 말투 복제), 진정성 진단서, 저주 부적, 레전드 썰.
전부 '실패하면 템플릿 폴백' — 키가 없어도 데모는 돌아간다.

프롬프트 원칙
- 출력 형식은 구조화 출력(output_config.format)으로 강제한다. 후처리로 추론 누출을 걷어내지 않는다.
- 스타일·숫자는 코드가 계산해 프롬프트에 넣고, 나온 결과도 코드가 검증한다(불일치 시 1회 재생성).
- few-shot은 고정 샘플이 아니라 "지금 입력과 비슷한 과거 상황"을 검색해 넣는다.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
from collections import Counter
from datetime import datetime

import anthropic
from dotenv import load_dotenv

import relationship as rel_mod
import stats
from core.sessions import relationship_messages
from parser import Message

load_dotenv()
MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5")
_WS = os.getenv("ANTHROPIC_WORKSPACE_ID")
client = anthropic.AsyncAnthropic(default_headers={"anthropic-workspace-id": _WS} if _WS else None)

ATTACH_KO = {"secure": "안정형", "anxious": "불안형", "avoidant": "회피형", "fearful": "혼란형"}
ENDING_KO = {"ghosted": "상대가 잠수/읽씹으로 끝냄 (나는 답을 기다리다 끝남)", "dumped": "상대가 나를 찼음 (내가 차였음 — 이별을 통보한 쪽은 상대)", "dumper": "내가 상대를 찼음 (내가 이별을 통보함)", "faded": "자연소멸", "mutual": "합의 이별", "ongoing": "아직 안 끝남"}

# 🔮 애착유형별 X 저주 부적 — (한자, 음, 뜻). 앞쪽이 밈 버전, 뒤가 정통 버전.
AMULETS = {
    "secure": [("前緣已斷\n後悔未斷", "전연이단 후회미단", "전 애인과의 인연은 끊겼으나 후회는 끊기지 않으리라"),
               ("有緣無愛", "유연무애", "인연은 있었으나 사랑은 끝났도다")],
    "anxious": [("前任常思", "전임상사", "평생 전 애인을 생각하리라"),
                ("欲忘愈憶", "욕망유억", "잊고 싶을수록 더욱 생각나리라")],
    "avoidant": [("戀愛即逃", "연애즉도", "연애만 시작하면 도망치리라"),
                 ("近則恐遠", "근즉공원", "가까워지면 두렵고, 멀어지면 또 외로우리라")],
    "fearful": [("來去無常", "래거무상", "왔다가 도망가고, 도망갔다가 다시 오리라"),
                ("欲近欲避", "욕근욕피", "만나고 싶으면서도 도망치고 싶으리라")],
    None: [("已讀無視\n永劫回歸", "이독무시 영겁회귀", "읽씹은 돌고 돌아 네게로 돌아오리라"),
           ("前任常思", "전임상사", "평생 전 애인을 생각하리라")],
}
CANNED_REPLIES = ["ㅇㅇ 근데 그건 네 생각이고", "바쁘다니까 자꾸", "미안한데 나 진짜 변한 거 없어", "그때도 말했잖아 ㅎㅎ",
                  "굳이 지금 이걸 물어봐야 돼?", "너 또 이런다 진짜", "나중에 연락할게"]
CURSES = ["읽씹하던 그 손가락,\n앞으로 오타만 나거라", "너의 모든 소개팅에\n어색한 침묵이 깃들기를", "새 연애 3일 만에\n전 애인 얘기 튀어나와라",
          "너의 인스타 스토리\n조회수 평생 한 자리수", "'바빴어'라는 변명,\n네 인생 최고 히트작 되거라"]

_META = ("시뮬레이터", "simulat", "역할", "샘플", "사용자", "assistant", "respond", "keep it", "per the")
_RE_POLITE = re.compile(r"(요|니다|세요|죠|십시오)[.!?~ㅠㅜ ]*$")
_RE_ASCII = re.compile(r"[A-Za-z]{3,}")
_RE_NUM = re.compile(r"\d+(?:\.\d+)?")
_RE_HANGUL = re.compile(r"[가-힣]{2,}")
_RE_HARM = re.compile(r"죽|피[를가]|칼|암[에이]|병[에이]|사고|장애|자살|폭[행력]|강간|자해|불구")


def _fmt_min(m: float | None) -> str:
    if m is None:
        return "–"
    if m < 1:
        return "1분 이내"
    return f"{m:.0f}분" if m < 60 else (f"{m/60:.1f}시간" if m < 1440 else f"{m/1440:.1f}일")


def _pct(xs: list, q: float):
    if not xs:
        return 0
    s = sorted(xs)
    return s[min(len(s) - 1, int(len(s) * q))]


def _bigrams(s: str) -> set[str]:
    t = re.sub(r"[^가-힣a-zA-Z0-9ㅋㅎㅠㅜ]", "", s)
    return {t[i:i + 2] for i in range(len(t) - 1)} or {t}


def _sim(a: str, b: str) -> float:
    A, B = _bigrams(a), _bigrams(b)
    return len(A & B) / len(A | B) if A and B else 0.0


def _text(resp) -> str:
    return "".join(b.text for b in resp.content if b.type == "text")


def _json(resp) -> dict:
    t = _text(resp).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, re.S)
        return json.loads(m.group(0)) if m else {}


def _seed(*parts) -> random.Random:
    return random.Random(int(hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()[:8], 16))


class Funeral:
    def __init__(self, all_msgs: list[Message], me: str, target: str, now: datetime, persona: dict | None):
        self.all, self.me, self.target, self.now = all_msgs, me, target, now
        self.persona = persona or {}
        self.rel = relationship_messages(all_msgs, me, target)
        self.brief = rel_mod.build(all_msgs, me, target, now, started_at=rel_mod.parse_date(self.persona.get("started_at")))
        self._turns_cache: list[dict] | None = None
        self._profile_cache: dict | None = None

    def context_line(self) -> str:
        p = self.persona
        bits = []
        if p.get("ending"):
            bits.append(f"이별 방식(사용자 진술): {ENDING_KO.get(p['ending'], p['ending'])}")
        if p.get("started_at"):
            bits.append(f"관계 시작일(사용자 진술): {p['started_at']}")
        if p.get("ended_at"):
            bits.append(f"헤어진 날: {p['ended_at']}")
        if p.get("context"):
            bits.append(f"사용자가 설명한 상황: {p['context'][:400]}")
        return "\n".join(bits) if bits else "(사용자가 추가로 알려준 이별 상황 없음)"

    def _started(self) -> datetime | None:
        s = self.persona.get("started_at")
        try:
            return datetime.fromisoformat(s) if s else None
        except ValueError:
            return None

    # ------------------------------------------------------------ 상대 말투 자료
    def turns(self) -> list[dict]:
        """같은 사람이 연달아 보낸 메시지 묶음(=카톡 '턴'). 미디어 제외, 30분 넘게 비면 새 턴."""
        if self._turns_cache is not None:
            return self._turns_cache
        out: list[dict] = []
        for m in self.rel:
            if m.is_media or not m.text.strip():
                continue
            if out and out[-1]["sender"] == m.sender and (m.ts - out[-1]["end"]).total_seconds() < 1800:
                out[-1]["texts"].append(m.text.strip()); out[-1]["end"] = m.ts
            else:
                out.append({"sender": m.sender, "texts": [m.text.strip()], "start": m.ts, "end": m.ts})
        self._turns_cache = out
        return out

    def pairs(self) -> list[dict]:
        """내 턴 → 바로 이어진 상대 턴 (6시간 안). {'me': str, 'them': [bubbles], 'gap_min': float, 'ts': datetime}"""
        ts = self.turns()
        out = []
        for a, b in zip(ts, ts[1:]):
            if a["sender"] == self.me and b["sender"] == self.target:
                gap = (b["start"] - a["end"]).total_seconds() / 60
                if gap <= 360:
                    out.append({"me": " / ".join(a["texts"])[:120], "them": b["texts"][:4], "gap_min": gap, "ts": b["start"]})
        return out

    def profile(self) -> dict:
        """상대 말투의 수치 프로필. 프롬프트에 넣고, 출력 검증에도 쓴다."""
        if self._profile_cache is not None:
            return self._profile_cache
        theirs = [t for t in self.turns() if t["sender"] == self.target]
        bubbles = [b for t in theirs for b in t["texts"]]
        n = max(1, len(bubbles))
        st = stats.my_style([m for m in self.rel if m.sender == self.target], self.target)
        lens = [len(b) for b in bubbles]
        counts = [len(t["texts"]) for t in theirs]
        # 붙여넣은 코드/영어 토큰(price, px, rng…)이 섞이므로 한글 표현만
        top_words = [w for w, _ in st.get("top_words", []) if _RE_HANGUL.fullmatch(w)][:12]
        starts = Counter(b.split()[0][:3] if b.split() else b[:2] for b in bubbles if len(b) >= 2)
        prof = {
            "n": len(bubbles),
            "len_p25": _pct(lens, .25), "len_p50": _pct(lens, .5), "len_p75": _pct(lens, .75), "len_p95": _pct(lens, .95),
            "bubbles_p50": _pct(counts, .5), "bubbles_p90": _pct(counts, .9), "counts": counts,
            "polite": round(sum(1 for b in bubbles if _RE_POLITE.search(b)) / n, 3),
            "period": round(sum(1 for b in bubbles if b.endswith(".")) / n, 3),
            "kkk": st.get("kkk_ratio", 0), "question": st.get("question_ratio", 0),
            "exclaim": st.get("exclaim_ratio", 0), "emoji": st.get("emoji_ratio", 0),
            "short_ack": round(sum(1 for b in bubbles if len(b) <= 3) / n, 3),
            "top_words": top_words,
            "starts": [w for w, _ in starts.most_common(10)],
            "late_night": st.get("late_night_ratio"),
        }
        self._profile_cache = prof
        return prof

    def _profile_lines(self) -> list[str]:
        p = self.profile()
        L = [f"- 버블 하나 길이: 절반이 {p['len_p50']}자 이하, 4분의 3이 {p['len_p75']}자 이하. {p['len_p95']}자를 넘는 건 20개 중 1개."]
        L.append(f"- 한 번에 보내는 버블 수: 보통 {p['bubbles_p50']}개, 많아야 {p['bubbles_p90']}개.")
        L.append("- 존댓말: " + ("거의 안 씀(반말)" if p["polite"] < .1 else f"섞어 씀({p['polite']:.0%})" if p["polite"] < .6 else "존댓말 위주"))
        L.append(f"- ㅋㅋ: 버블의 {p['kkk']:.0%}에 등장" + (" (거의 안 씀)" if p["kkk"] < .05 else " (자주)" if p["kkk"] > .4 else ""))
        L.append(f"- 물음표 {p['question']:.0%}, 느낌표 {p['exclaim']:.0%}, 이모지 {p['emoji']:.0%}, 마침표로 끝남 {p['period']:.0%}, 3자 이하 단답 {p['short_ack']:.0%}")
        if p["top_words"]:
            L.append(f"- 자주 쓰는 표현: {', '.join(p['top_words'])}")
        if p["starts"]:
            L.append(f"- 버블을 자주 시작하는 말(빈도순): {', '.join(p['starts'])} — 이 분포대로 다양하게. 한 표현만 반복하면 티 남.")
        return L

    def retrieve(self, query: str, k: int = 6) -> list[dict]:
        """지금 사용자 입력과 가장 비슷한 과거 '내 말'을 찾아, 그때 상대가 실제로 어떻게 받았는지 돌려준다."""
        ps = self.pairs()
        scored = sorted(((_sim(query, p["me"]), i) for i, p in enumerate(ps)), reverse=True)
        picked = [ps[i] for s, i in scored[:k] if s > 0.05]
        return picked

    def shared_history(self) -> str:
        """소환술용 '우리 사이' 배경 — 전부 코드가 뽑은 사실. 헤어진 지 며칠, 마지막 실제 대화 원문, 둘 사이 자주 나온 화제."""
        b = self.brief
        start = self.persona.get("started_at") or b["range"][0][:10]
        ended = self.persona.get("ended_at")
        last_ts = self.rel[-1].ts if self.rel else None
        lines = [f"- 관계 기간: {start} ~ {ended or '(끝난 날 미입력)'}"]
        if ended:
            try:
                d = (self.now.date() - datetime.fromisoformat(ended).date()).days
                lines.append(f"- 헤어진 지 {d}일" if d >= 0 else "- 아직 안 끝남(사용자 진술)")
            except ValueError:
                pass
        if last_ts:
            d2 = (self.now - last_ts).days
            if d2 >= 2:
                lines.append(f"- 마지막으로 실제 카톡한 지 {d2}일. 지금 사용자가 보내는 톡은 그 뒤 처음 온 연락이다.")
            else:
                lines.append("- 마지막 카톡이 어제/오늘이다. 아래 '마지막 실제 대화' 직후에 이어지는 톡으로 받는다.")
        # 둘 사이 자주 나온 화제 (양쪽 메시지, 한글 단어만)
        st_all = stats.my_style(self.rel, self.me)
        st_all_t = stats.my_style(self.rel, self.target)
        cnt = Counter()
        for st in (st_all, st_all_t):
            for w, c in st.get("top_words", []):
                if _RE_HANGUL.fullmatch(w) and w not in ("샵검색",):   # 카톡 '#검색' 잔재
                    cnt[w] += c
        topics = [w for w, _ in cnt.most_common(15)]
        if topics:
            lines.append(f"- 둘이 자주 꺼낸 말/화제: {', '.join(topics)}")
        # 끝나기 직전 실제 대화 12개 (원문, 날짜)
        tail = [m for m in self.rel if not m.is_media and m.text.strip()][-12:]
        if tail:
            lines.append("- 마지막 실제 대화 (이걸 겪은 상태로 답한다):")
            for m in tail:
                who = "나" if m.sender == self.me else self.target
                lines.append(f"    {m.ts:%m/%d %H:%M} {who}: {m.text.strip()[:80]}")
        return "\n".join(lines)

    def summon_system(self) -> str:
        p = self.profile()
        b = self.brief
        recent = [x for x in self.pairs()][-14:]
        persona_line = ", ".join(x for x in [self.persona.get("mbti"), ATTACH_KO.get(self.persona.get("attachment") or "")] if x)
        pair_lines = "\n".join(f"- 나: {x['me']}\n  {self.target}: " + " | ".join(x["them"]) for x in recent)
        return f"""너는 '{self.target}'이 카톡에서 실제로 어떻게 답하는지 재현하는 시뮬레이터다. 사용자는 {self.target}의 전 연인/썸이고, 지금 미련 섞인 톡을 던진다. 사용자는 이게 시뮬레이터라는 걸 알고 있고, 원하는 건 위로가 아니라 "이 사람이라면 진짜 이렇게 답했겠구나" 하는 현실감이다.

## {self.target}의 말투 (카톡 {p['n']}개에서 코드로 계산)
{chr(10).join(self._profile_lines())}
- 성격 힌트(사용자 입력): {persona_line or '없음'}
- 관계 상태: {b['stages']['current_label']}. 상대 답장 중앙값 {_fmt_min(b['symmetry']['reply']['their_median_min'])}.
- {self.context_line().replace(chr(10), ' / ')}
  → 데이터와 다르면 사용자 진술을 우선한다. 끝난 관계면 끝난 사람처럼: 붙잡지 않고, 미지근하고, 설명이 짧다.

## 우리 사이 (데이터)
{self.shared_history()}

## 최근 실제 대화 (나 → {self.target}). "|"는 버블 구분
{pair_lines}

## 답하는 법
- 위 사람이 지금 이 톡을 받았을 때 보낼 법한 버블을 그대로 쓴다. '우리 사이'의 마지막 대화와 사용자가 말한 사정을 기억하는 사람으로서 답한다 — 사용자가 그때 일을 꺼내면 그 대화를 아는 티가 나야 한다. 단, 데이터에 없는 사건·사람·장소는 지어내지 않는다. 띄어쓰기·맞춤법·어미·ㅋㅋ 습관까지 위 샘플 그대로. 더 다정하거나 더 설명적이면 실패.
- 같은 시작("ㅇㅇ", "아니")을 매번 반복하지 않는다. 샘플의 다양한 시작을 따른다.
- 이어지는 시스템 메시지에 "비슷한 상황에서 실제로 했던 답"과 "이번 답의 길이·버블 수"가 온다. 그걸 가장 우선한다.
- 자해·죽고 싶다는 신호가 보이면 시뮬을 멈추고 이렇게만 답한다: "이건 시뮬레이터야. 힘들면 1393(자살예방상담)에 전화해줘"
- 출력은 JSON {{"bubbles": ["...", "..."]}} 하나. 각 원소가 카톡 버블 하나. 따옴표·설명·영어 없음."""

    def _turn_spec(self, query: str, hist: list[dict]) -> tuple[str, dict]:
        """이번 답의 버블 수·길이를 상대의 실제 분포에서 샘플링해 지정하고, 이 대화에서 이미 쓴 시작 표현을 알려준다."""
        p = self.profile()
        rng = _seed(query, len(hist))
        counts = [c for c in p["counts"] if c <= 3] or [1]
        n_bub = rng.choice(counts)
        lo, hi = max(2, p["len_p25"]), max(p["len_p25"] + 4, p["len_p75"])
        target_len = rng.randint(lo, hi)
        sim = self.retrieve(query)
        lines = []
        if sim:
            lines.append(f"## 비슷한 말을 들었을 때 {self.target}이 실제로 한 답 (이 결을 우선 참고)")
            lines += [f"- 나: {x['me']}\n  {self.target}: " + " | ".join(x["them"]) for x in sim]
        used = [w for m in hist if m["role"] == "assistant" for w in [m["content"].split("\n")[0].split(" ")[0][:3]] if w]
        lines.append(f"## 이번 답 스펙\n- 버블 {n_bub}개, 버블당 {target_len}자 안팎 (합쳐서 {n_bub * target_len}자 넘기지 말 것).")
        if used:
            lines.append(f"- 이 대화에서 이미 쓴 시작 표현: {', '.join(dict.fromkeys(used))} → 이번엔 다른 시작으로.")
        return "\n".join(lines), {"n_bubbles": n_bub, "target_len": target_len, "similar": len(sim)}

    def style_check(self, bubbles: list[str]) -> list[str]:
        """코드가 계산한 상대 스타일과 어긋나는 점. 비면 통과."""
        p = self.profile()
        issues = []
        if not bubbles or not any(b.strip() for b in bubbles):
            return ["empty"]
        joined = " ".join(bubbles)
        max_len = max(25, int(p["len_p95"] * 1.2))
        if any(len(b) > max_len for b in bubbles):
            issues.append(f"버블이 너무 김({max(len(b) for b in bubbles)}자 > {max_len}자)")
        if p["polite"] < .1 and any(_RE_POLITE.search(b) for b in bubbles):
            issues.append("존댓말 사용(이 사람은 반말)")
        if p["polite"] > .8 and not any(_RE_POLITE.search(b) for b in bubbles):
            issues.append("반말 사용(이 사람은 존댓말)")
        if p["kkk"] < .05 and "ㅋㅋ" in joined:
            issues.append("ㅋㅋ 사용(이 사람은 거의 안 씀)")
        if p["exclaim"] < .02 and "!" in joined:
            issues.append("느낌표 사용(이 사람은 안 씀)")
        if p["emoji"] < .02 and stats._RE_EMOJI.search(joined):
            issues.append("이모지 사용(이 사람은 안 씀)")
        if _RE_ASCII.search(joined) or any(k in joined.lower() for k in _META):
            issues.append("영어/메타 단어")
        return issues

    async def summon(self, messages: list[dict]) -> dict:
        hist = [{"role": m["role"], "content": m["content"]} for m in messages if m.get("content")]
        opener = not hist
        if hist and hist[-1]["role"] != "user":
            return {"reply": random.choice(CANNED_REPLIES), "bubbles": None, "fallback": True}
        if opener:   # 사용자가 아직 아무 말도 안 함 → 상대가 먼저 던지는 첫 톡 (마지막 실제 대화 직후처럼)
            query = ""
            spec_text = (f"## 첫 톡\n사용자는 아직 아무 말도 안 했다. '우리 사이'의 마지막 실제 대화 바로 다음에 {self.target}이 먼저 보낼 법한 톡을 버블 1~2개로 써라. "
                         "그 대화를 이어받거나(물건, 마지막 말, 미뤄둔 얘기), 며칠 지난 뒤 툭 던지는 말이어도 된다. 사용자의 말을 지어내지 말고, 새 사건도 만들지 마라.")
            spec = {"n_bubbles": 2, "target_len": self.profile()["len_p50"], "similar": 0, "opener": True}
            hist = [{"role": "user", "content": "(아직 아무 말도 안 함)"}]
        else:
            query = hist[-1]["content"]
            spec_text, spec = self._turn_spec(query, hist)
            if hist[0]["role"] == "assistant":   # 상대가 먼저 던진 첫 톡으로 시작한 대화 — API는 첫 메시지가 user여야 한다
                hist = [{"role": "user", "content": "(아직 아무 말도 안 함)"}] + hist
        system = [{"type": "text", "text": self.summon_system(), "cache_control": {"type": "ephemeral"}}]
        fmt = {"type": "json_schema", "schema": {"type": "object", "properties": {"bubbles": {"type": "array", "items": {"type": "string"}}},
                                                 "required": ["bubbles"], "additionalProperties": False}}
        msgs = hist + [{"role": "system", "content": spec_text}]
        try:
            bubbles, issues, retried = [], ["empty"], False
            for attempt in range(2):
                resp = await client.messages.create(model=MODEL, max_tokens=3000, output_config={"effort": "medium", "format": fmt},
                                                    system=system, messages=msgs)
                bubbles = [str(x).strip() for x in (_json(resp).get("bubbles") or []) if str(x).strip()][:3]
                issues = self.style_check(bubbles)
                if not issues:
                    break
                retried = True
                msgs = hist + [{"role": "system", "content": spec_text + f"\n\n## 직전 시도의 문제 (고쳐서 다시)\n- " + "\n- ".join(issues)}]
            if not bubbles:
                return {"reply": random.choice(CANNED_REPLIES), "bubbles": None, "fallback": True}
            if issues:   # 재생성도 실패 → 코드가 최소 정리
                bubbles = [b.replace("!", "").strip()[:max(25, int(self.profile()["len_p95"] * 1.2))] for b in bubbles]
            return {"reply": "\n".join(bubbles), "bubbles": bubbles,
                    "check": {"ok": not issues, "retried": retried, "issues": issues, **spec}}
        except Exception as e:  # noqa: BLE001
            return {"reply": random.choice(CANNED_REPLIES), "bubbles": None, "fallback": True, "error": str(e)[:200]}

    # ------------------------------------------------------------ 진정성 진단서
    def _facts(self) -> list[str]:
        """코드로 계산한 사실. 사용자가 시작일을 알려줬으면 그 이후 구간만."""
        b = self.brief
        r = b["symmetry"]["reply"]; bi = b["bias"]; w = b["waiting"]; sg = b["signals"]
        start = self._started()
        rng0 = max(b["range"][0][:10], start.date().isoformat()) if start else b["range"][0][:10]
        end = self.persona.get("ended_at") or b["range"][1][:10]
        n_msgs = sum(1 for m in self.rel if not start or m.ts >= start)
        segs = [s for s in b["stages"]["segments"] if not start or s.get("start", "9999") >= start.date().isoformat()] or b["stages"]["segments"][-3:]
        labels = []
        for s in segs:
            if not labels or labels[-1] != s["label"]:
                labels.append(s["label"])
        facts = [
            f"기간 {rng0} ~ {end}, 메시지 {n_msgs}개",
            f"단계 흐름: {' → '.join(labels[-5:])} (마지막 {b['stages']['current_label']})",
            f"온도 {b['temperature'].get('temp')}°, 최근 주간 변화 {b['temperature'].get('delta_week')}",
            f"답장 중앙값: 나 {_fmt_min(r['my_median_min'])} / 상대 {_fmt_min(r['their_median_min'])}",
            f"신호 판정: {sg['title']} (나 {sg['me']['score']} / 상대 {sg['them']['score']})",
        ]
        if bi["reply_speed"].get("times_faster"):   # 내 다른 방이 없으면 baseline이 없어 None → 사실에서 뺀다
            facts.insert(4, f"나는 이 사람에게 다른 사람들보다 {bi['reply_speed']['times_faster']}배 빨리 답함 ({_fmt_min(bi['reply_speed']['to_target_min'])} vs 남들에겐 {_fmt_min(bi['reply_speed']['to_others_min'])})")
        if w:
            facts.append(f"상대 마지막 메시지 “{w['text'][:40]}” 에 {w['age_hours']}시간째 내가 답 안 함 (평소 {_fmt_min(w['usual_reply_min'])})")
        events = [e for e in b["events"] if not start or e["week_start"] >= start.date().isoformat()][-3:]
        for e in events:
            facts.append(f"{e['week_start']} 주: 온도가 전주보다 {e['delta']:+}° 변함 (주요 요인: {e['top_factor']['label'] if e['top_factor'] else '–'})")
        return facts

    def template_eulogy(self) -> str:
        b = self.brief; r = b["symmetry"]["reply"]; bi = b["bias"]; w = b["waiting"]
        parts = [f"{self.target}은(는) 나쁜 사람이 아니라, 맞지 않는 사람이었어요."]
        if r["their_median_min"] is not None:
            parts.append(f"평소 {_fmt_min(r['their_median_min'])} 안에 답하던 사람이 {('%s시간째 답이 없는 건' % w['age_hours']) if w else '느려진 건'} 미움이 아니라 무관심의 신호였고, 무관심은 설득으로 바뀌지 않아요.")
        if bi["reply_speed"]["times_faster"] and bi["reply_speed"]["times_faster"] > 1.5:
            parts.append(f"당신은 이 사람에게만 평소보다 {bi['reply_speed']['times_faster']}배 빨리 답했어요. 지금 슬픈 건 그 사람을 잃어서가 아니라, 쏟은 마음이 아까워서예요.")
        else:
            parts.append("지금 슬픈 건 그 사람을 잃어서가 아니라, 쏟은 마음이 아까워서예요.")
        parts.append("그 마음, 당신은 다시 채울 수 있어요. 오늘은 여기까지. 잘 보내주세요. 🕊️")
        return " ".join(parts)

    _EULOGY_BANNED = re.compile(r"마음이 (식|떠)|질렸|싫어(졌|하)|귀찮|사랑하지 않|다른 사람이 생|속으로는|두 분|양쪽 다|서로에게|매달린 게 아니|시간이 약|더 좋은 사람|탓이 아니")
    _EULOGY_CLOSE = re.compile(r"놓아|보내 ?[주줘]|괜찮아요|여기까지|내려놓|두어도|둬도|접어[두둬]|안 ?해도 (돼|되)|않아도 (돼|되)")

    def eulogy_check(self, text: str, facts: list[str]) -> list[str]:
        issues = []
        n = len(text)
        if n < 120:
            issues.append(f"너무 짧음({n}자)")
        if n > 380:
            issues.append(f"너무 김({n}자, 380자 이하)")
        nums = {x for f in facts for x in _RE_NUM.findall(f)} - {"0"}
        used = {x for x in nums if x in text}
        if len(used) < 2:
            issues.append(f"사실 인용 부족(숫자 {len(used)}개, 2개 이상)")
        if len(_RE_NUM.findall(text)) > 5:
            issues.append("숫자 나열 과다(5개 이하)")
        m = self._EULOGY_BANNED.search(text)
        if m:
            issues.append(f"금지 표현 '{m.group(0)}'")
        if not self._EULOGY_CLOSE.search(text[-60:]):
            issues.append("마지막 문장이 놓아주기로 끝나지 않음")
        if len(stats._RE_EMOJI.findall(text)) > 1:
            issues.append("이모지 2개 이상")
        return issues

    async def eulogy(self) -> dict:
        facts = self._facts()
        fact_block = "\n".join(f"[F{i + 1}] {f}" for i, f in enumerate(facts))
        prompt = f"""'{self.target}'과의 관계에 대한 진정성 진단서를 써. 읽는 사람은 이 관계를 막 잃은 사용자야. 아래 사실은 카톡 데이터에서 코드로 계산한 것이고, 진단서는 이 사실 위에서만 선다.

[사실]
{fact_block}

[사용자가 알려준 이별 상황]
{self.context_line()}

[구조 — 이 순서로, 5~6문장, 250~350자]
1. 관찰 (2문장): 사실 중 2개만 골라 숫자를 그대로 인용하며 관계의 '모양'을 말한다. 상대가 왜 그랬는지는 말하지 않는다 — 우리는 상대 마음을 모른다. 대화의 형태만 안다.
2. 인정 (2문장): 사용자가 쏟은 마음을 사실로 짚는다 (답장 속도 편향, 기다린 시간 같은 '나' 쪽 숫자). 그 마음이 잘못이 아니었다고 말한다.
3. 놓아주기 (1~2문장): 관계를 보내주라는 말로 끝낸다. 위로는 짧고, 명령이 아니라 허락처럼.

[뼈대 — 빈칸을 이 관계의 사실로 채운다. 문장은 네가 새로 쓴다]
관찰: 「(기간·양 사실)했고, (변화 사실)했어요.」 「그 사람 마음은 모르지만, 대화의 모양은 (사실이 보여주는 형태)였어요.」
인정: 「당신은 (나 쪽 숫자 사실)했어요.」 「그건 (부정적 해석)이 아니라 (긍정적 재해석)이었어요.」
놓아주기: 「(짧은 공감) — 이제 (보내주라는 허락).」

톤 기준: 상담사가 아니라 오래 본 친구가 조용히 말해주는 느낌. 뻔한 위로 문구("시간이 약", "더 좋은 사람", "당신 탓이 아니에요")는 쓰지 않는다. 이 사람의 숫자가 아니면 못 쓰는 문장이어야 한다.

[하지 말 것]
- 상대의 마음·의도 단정 ("마음이 식었다", "질렸다", "다른 사람이 생겼다")
- "두 분", "서로에게" 같은 양쪽 관점 — 이 진단서는 사용자 한 사람에게 쓰는 편지다
- 숫자는 전체에서 3~4개만. 5개를 넘기면 검증에서 탈락한다. 날짜는 1개까지, 단계 이름을 전부 나열하지 않는다
- 상투적 반전·위로 ("매달린 게 아니라", "시간이 약", "더 좋은 사람", "당신 탓이 아니에요")
- 이모지는 마지막에 1개까지

말투: 부드러운 존댓말("~에요"). 제목 없이 본문만. 사용자를 부를 땐 '당신'."""
        fmt = {"type": "json_schema", "schema": {"type": "object", "properties": {"text": {"type": "string"}, "cited": {"type": "array", "items": {"type": "string"}}},
                                                 "required": ["text", "cited"], "additionalProperties": False}}
        try:
            msgs = [{"role": "user", "content": prompt}]
            text, issues, first_issues = "", ["empty"], []
            for attempt in range(2):
                resp = await client.messages.create(model=MODEL, max_tokens=4000, output_config={"effort": "medium", "format": fmt}, messages=msgs)
                data = _json(resp)
                text = str(data.get("text", "")).strip()
                issues = self.eulogy_check(text, facts)
                if not issues:
                    break
                first_issues = issues
                msgs = [{"role": "user", "content": prompt}, {"role": "assistant", "content": _text(resp)},
                        {"role": "user", "content": "코드 검증에서 걸렸어. 아래를 고쳐서 같은 JSON으로 다시 써.\n- " + "\n- ".join(issues)}]
            if not text:
                return {"text": self.template_eulogy(), "fallback": True}
            return {"text": text, "check": {"ok": not issues, "retried": bool(first_issues), "first_issues": first_issues, "issues": issues}}
        except Exception as e:  # noqa: BLE001
            return {"text": self.template_eulogy(), "fallback": True, "error": str(e)[:200]}

    # ------------------------------------------------------------ 저주 부적 (애착유형별 사자성어 + 맞춤 한 줄)
    def _curse_facts(self) -> list[str]:
        b = self.brief; r = b["symmetry"]["reply"]; w = b["waiting"]; p = self.profile()
        facts = [f"답장 중앙값 {_fmt_min(r['their_median_min'])}"]
        if p["top_words"]:
            facts.append(f"자주 쓰는 말: {', '.join(p['top_words'][:6])}")
        facts.append(f"버블 절반이 {p['len_p50']}자 이하 단답" if p["len_p50"] <= 8 else f"버블 중앙값 {p['len_p50']}자")
        if p["kkk"] > .3:
            facts.append(f"ㅋㅋ를 버블 {p['kkk']:.0%}에 붙임")
        elif p["kkk"] < .05:
            facts.append("ㅋㅋ를 거의 안 씀")
        if p["late_night"] and p["late_night"] > .25:
            facts.append(f"메시지 {p['late_night']:.0%}가 새벽")
        if p["short_ack"] > .3:
            facts.append(f"3자 이하 단답이 {p['short_ack']:.0%}")
        if w:
            facts.append(f"마지막 메시지 “{w['text'][:30]}” 에 {w['age_hours']}시간째 서로 침묵")
        if self.persona.get("ending"):
            facts.append(ENDING_KO.get(self.persona["ending"], self.persona["ending"]))
        return facts

    def _pick_curse(self, cands: list[dict], facts: list[str]) -> tuple[str | None, list[str]]:
        """모델이 좋은 순으로 낸 후보 중, 코드 게이트(26자 이하·위해 표현 없음·상대 패턴 포함)를 통과한 첫 줄.
        부적은 한 사람당 한 번이라 실행 간 다양성은 필요 없다 — 제일 좋은 걸 고르면 된다."""
        p = self.profile()
        keys = set(p["top_words"][:8]) | {x for f in facts for x in _RE_NUM.findall(f)} | {"읽씹", "답장", "ㅋㅋ", "새벽", "단답", "잠수", "분", "시간"}
        log = []
        for c in cands:
            line = str(c.get("line", "")).strip().replace("\n", " ")
            if len(line) > 2 and line[0] == line[-1] and line[0] in "\"'" and line.count(line[0]) == 2:
                line = line[1:-1].strip()   # 통째로 감싼 따옴표만 벗긴다 (안쪽 인용 부호는 보존)
            if not line:
                continue
            if len(line) > 26:
                log.append(f"{line} → 길이 {len(line)}"); continue
            if _RE_HARM.search(line):
                log.append(f"{line} → 위해 표현"); continue
            if not any(k in line for k in keys):
                log.append(f"{line} → 패턴 없음"); continue
            return line, log
        return None, log

    async def curse(self) -> dict:
        attach = self.persona.get("attachment")
        hanja, reading, meaning = AMULETS.get(attach, AMULETS[None])[0]
        facts = self._curse_facts()
        prompt = f"""부적에 이미 큰 글씨로 '{hanja.replace(chr(10), ' ')}'({reading}: {meaning})이 박혀 있어. 그 아래 작게 들어갈 '{self.target}' 맞춤 저주 한 줄 후보를 3개, 제일 좋은 것부터 순서대로 써.

[{self.target}의 카톡 패턴 (코드 계산)]
{chr(10).join('- ' + f for f in facts)}

[저주의 결]
- 유치하고 소심하다. 진짜 해코지가 아니라 "그 버릇 그대로 돌려받아라" 수준. 신체·질병·사고·죽음 없음.
- 위 패턴 중 하나를 그대로 박는다 — 그 사람만 찔리는 저주가 좋은 저주다. 3개가 서로 다른 패턴을 쓰게.
- 22자 이내 한 줄 (공백 포함, 넘으면 탈락). 명령형/기원형으로 끝난다 ("~해라", "~되거라", "~기를").

[좋은 예 — 결만 참고, 패턴은 이 사람 것으로]
- "잘자" 보낸 밤마다 와이파이 끊겨라
- 'ㅇㅇ' 칠 때마다 자동완성 '응 사랑해'
- 새 연애 3일 만에 내 얘기 튀어나와라
- 1분컷 답장, 이제 배달앱한테만 받아라
- 새벽 2시 카톡 알림, 평생 광고만 오거라
- 읽씹한 만큼 엘리베이터 코앞에서 닫혀라

JSON: {{"candidates": [{{"line": "...", "pattern": "쓴 패턴"}}, ...]}}"""
        base = {"hanja": hanja, "reading": reading, "meaning": meaning, "attachment": attach,
                "attachment_label": ATTACH_KO.get(attach or "", "유형 미상")}
        fmt = {"type": "json_schema", "schema": {"type": "object", "properties": {"candidates": {"type": "array", "items": {
            "type": "object", "properties": {"line": {"type": "string"}, "pattern": {"type": "string"}}, "required": ["line", "pattern"], "additionalProperties": False}}},
            "required": ["candidates"], "additionalProperties": False}}
        try:
            resp = await client.messages.create(model=MODEL, max_tokens=3000, output_config={"effort": "low", "format": fmt},
                                                messages=[{"role": "user", "content": prompt}])
            cands = _json(resp).get("candidates") or []
            line, log = self._pick_curse(cands, facts)
            if line is None:   # 전부 탈락 → 22자 이하인 첫 후보라도, 그것도 없으면 템플릿
                short = [str(c.get("line", "")).strip() for c in cands if 0 < len(str(c.get("line", "")).strip()) <= 26 and not _RE_HARM.search(str(c.get("line", "")))]
                line = short[0] if short else random.choice(CURSES).replace("\n", " ")
            return {**base, "line": line[:40], "text": line[:40], "candidates": [c.get("line") for c in cands], "rejected": log}
        except Exception as e:  # noqa: BLE001
            line = random.choice(CURSES).replace("\n", " ")
            return {**base, "line": line, "text": line, "fallback": True, "error": str(e)[:200]}

    # ------------------------------------------------------------ 비문 (공동묘지 묘비 제목 — 어그로성 한 줄)
    def _epitaph_facts(self, causes: list[dict] | None, days: int | None) -> list[str]:
        b = self.brief; r = b["symmetry"]["reply"]; w = b["waiting"]; p = self.profile()
        facts = []
        if days:
            facts.append(f"관계 {days}일 ({days // 30}개월)" if days >= 60 else f"관계 {days}일")
        if self.persona.get("ending"):
            facts.append(ENDING_KO.get(self.persona["ending"], self.persona["ending"]))
        if self.persona.get("context"):
            facts.append("사용자가 말한 사정: " + self.persona["context"].replace("\n", " / ")[:300])
        for c in (causes or [])[:2]:
            ev = c.get("evidence") or ""
            facts.append(f"사망 원인 {c.get('pct')}%: {c.get('label')} ({ev})" if ev else f"사망 원인 {c.get('pct')}%: {c.get('label')}")
        facts.append(f"답장 중앙값 나 {_fmt_min(r['my_median_min'])} / 상대 {_fmt_min(r['their_median_min'])}")
        if w:
            facts.append(f"상대 마지막 말 “{w['text'][:30]}” 에 {w['age_hours']}시간째 답 없음")
        last = next((m for m in reversed(self.rel) if not m.is_media and m.text.strip() and not m.text.startswith("파일:")), None)
        if last:
            facts.append(f"마지막 톡({'나' if last.sender == self.me else '상대'}): “{last.text.strip()[:40]}”")
        if p["top_words"]:
            facts.append(f"상대 입버릇: {', '.join(p['top_words'][:4])}")
        return facts

    async def epitaph(self, causes: list[dict] | None = None, days: int | None = None) -> dict:
        facts = self._epitaph_facts(causes, days)
        prompt = f"""공동묘지에 세울 내 관계의 묘비 제목을 3개, 제일 좋은 것부터 써. 지나가던 조문객이 "헐 뭐야" 하고 멈춰서 헌화 누르게 만드는 커뮤니티 썰 제목 같은 한 줄이다.

[이 관계의 사실 (코드 계산 + 사용자 진술)]
{chr(10).join('- ' + f for f in facts)}

[결]
- 12~28자. 구체적 숫자·상황 하나가 들어가면 강하다 (기간, 답장 속도, 마지막 말, 이별 방식).
- 사용자가 말한 사정이 있으면 그게 1순위 재료. 없으면 사망 원인·마지막 톡.
- 어그로지만 상대 비하·욕설·실명 없음. 자조는 OK. 이모지 없음. 따옴표로 감싸지 않는다.
- 마지막 톡을 인용하면 따옴표 안에 짧게.

[좋은 예 — 결만 참고]
- 3년 연애 후 '우리 잠깐 시간을 갖자' → 잠수
- 200일 선물 주고 그날 밤 환승 발각
- 바쁘다며 스토리는 1분마다 올리던 그대
- 읽씹 6시간, 답장은 'ㅇㅇ' 두 글자
- 1분컷 답장 175일, 끝은 "지쳤어" 한 마디

JSON: {{"candidates": ["...", "...", "..."]}}"""
        fmt = {"type": "json_schema", "schema": {"type": "object", "properties": {"candidates": {"type": "array", "items": {"type": "string"}}},
                                                 "required": ["candidates"], "additionalProperties": False}}
        try:
            resp = await client.messages.create(model=MODEL, max_tokens=2000, output_config={"effort": "low", "format": fmt},
                                                messages=[{"role": "user", "content": prompt}])
            cands = [str(c).strip().strip('"“”') for c in (_json(resp).get("candidates") or [])]
            ok = [c for c in cands if 6 <= len(c) <= 34 and self.target not in c and not _RE_HARM.search(c) and not stats._RE_EMOJI.search(c)]
            if not ok:
                return {"epitaph": None, "candidates": cands, "fallback": True}
            return {"epitaph": ok[0], "candidates": cands}
        except Exception as e:  # noqa: BLE001
            return {"epitaph": None, "fallback": True, "error": str(e)[:200]}


# ------------------------------------------------------------ 레전드 썰 매칭 (웹 검색)
LEGEND_DOMAINS = ["pann.nate.com", "gall.dcinside.com", "m.dcinside.com", "theqoo.net", "instiz.net", "fmkorea.com",
                  "teamblind.com", "everytime.kr", "ppomppu.co.kr", "clien.net", "82cook.com", "bobaedream.co.kr", "orbi.kr", "dogdrip.net"]
LEGEND_SCHEMA_HINT = """{"stories": [{"title": "...", "source": "네이트판 톡 / 디시 연애갤 / 더쿠 ...", "url": "https://...",
  "summary": "글의 상황을 내 말로 2문장 요약 (원문 복사 금지)", "match_points": ["내 데이터와 겹치는 점 1", "겹치는 점 2"],
  "similarity": 0~100 정수, "hit": "현타 포인트 한 문장"}]}"""


def _extract_json(text: str) -> dict | None:
    cands = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S) or []
    start = text.rfind('{"stories"')
    if start >= 0:
        cands.append(text[start:])
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        cands.append(m.group(0))
    for c in cands:
        try:
            return json.loads(c)
        except json.JSONDecodeError:
            # 뒤가 잘린 경우 마지막 완결 객체까지만
            end = c.rfind("}]}")
            if end > 0:
                try:
                    return json.loads(c[:end + 3])
                except json.JSONDecodeError:
                    pass
    return None


def _legend_facts(fun: "Funeral") -> list[str]:
    b = fun.brief; r = b["symmetry"]["reply"]; w = b["waiting"]
    facts = [
        f"관계 단계 흐름: {' → '.join(s['label'] for s in b['stages']['segments'][-4:])}",
        f"상대 답장 중앙값 {_fmt_min(r['their_median_min'])}, 내 답장 중앙값 {_fmt_min(r['my_median_min'])}",
        f"나는 이 사람에게 다른 사람보다 {b['bias']['reply_speed']['times_faster']}배 빨리 답함",
    ]
    if w:
        facts.append(f"상대 마지막 메시지 “{w['text'][:40]}” 에 {w['age_hours']}시간째 무응답")
    persona = ", ".join(x for x in [fun.persona.get("mbti"), ATTACH_KO.get(fun.persona.get("attachment") or "")] if x)
    facts.append(f"상대 성향(사용자 입력): {persona or '미입력'}")
    facts.append(fun.context_line().replace("\n", " / "))
    return facts


async def _legend_queries(facts: list[str]) -> list[str]:
    """1단계: 데이터 사실 → 커뮤니티 검색어 3개. 검색은 안 하고 검색어만 만든다."""
    prompt = f"""아래는 어떤 사람의 연애/이별 상황을 카톡 데이터로 요약한 것이다. 네이트판·디시 연애갤·더쿠 같은 한국 커뮤니티에서 '비슷한 썰'을 찾기 위한 검색어 3개를 만들어.

{chr(10).join('- ' + f for f in facts)}

검색어 규칙: 한국어, 2~4단어, 커뮤니티 사람들이 제목에 실제로 쓰는 말 (예: "회피형 잠수 이별", "읽씹 후 잠수 네이트판", "연락 뜸해지다 헤어짐"). 3개는 서로 다른 각도(이별 방식 / 상대 성향 / 내 행동 패턴)여야 한다. 상황에 없는 걸 지어내지 마."""
    fmt = {"type": "json_schema", "schema": {"type": "object", "properties": {"queries": {"type": "array", "items": {"type": "string"}}},
                                             "required": ["queries"], "additionalProperties": False}}
    resp = await client.messages.create(model=MODEL, max_tokens=1500, output_config={"effort": "low", "format": fmt},
                                        messages=[{"role": "user", "content": prompt}])
    qs = [str(q).strip() for q in (_json(resp).get("queries") or []) if str(q).strip()]
    return list(dict.fromkeys(qs))[:3]


async def legends_for(fun: "Funeral") -> dict:
    """내 관계 데이터 + 사용자 진술 → (1) 검색어 생성 → (2) 검색·매칭. 두 단계를 분리해 검색어 품질을 따로 본다."""
    facts = _legend_facts(fun)
    try:
        planned = await _legend_queries(facts)
    except Exception as e:  # noqa: BLE001
        planned = []
        plan_err = str(e)[:120]
    else:
        plan_err = None
    query_block = ("\n".join(f'- "{q}"' for q in planned)) if planned else '- (직접 2~3개 만들어 검색: 예 "회피형 잠수 이별 썰", "읽씹 후 잠수 네이트판")'
    prompt = f"""아래는 사용자의 카톡 데이터로 계산한 관계 사실과, 사용자가 직접 알려준 이별 상황이야.
이와 **비슷한 상황의 실제 커뮤니티 썰**을 웹에서 찾아서 2~3개 골라줘.

[데이터 사실]
{chr(10).join('- ' + f for f in facts)}

[검색어 — 각각 web_search 한 번씩 그대로 검색. 결과가 빈약하면 한 번만 변형해서 추가 검색]
{query_block}

[규칙]
1. 실제로 존재하는 글만. URL은 검색 결과에 있던 것 그대로. 지어내지 마.
2. 요약은 원문을 복사하지 말고 상황만 내 말로 2문장. 실명·연락처 등 개인정보 제외.
3. match_points는 위 [데이터 사실]의 항목을 근거로 구체적으로 ("상대 답장 중앙값 1분 이내였는데 마지막엔 40시간 무응답" 처럼 숫자 포함).
4. similarity는 겹치는 사실 수에 비례 (1개 40 / 2개 65 / 3개 이상 85+).
5. 마지막에 아래 JSON만 출력 (설명 금지):
{LEGEND_SCHEMA_HINT}"""
    try:
        tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 6, "allowed_domains": LEGEND_DOMAINS,
                  "user_location": {"type": "approximate", "country": "KR", "timezone": "Asia/Seoul"}}]
        messages = [{"role": "user", "content": prompt}]
        text = ""
        queries: list[str] = []
        for _ in range(4):   # pause_turn(검색이 길어질 때 서버가 중간 정지) 이어받기
            resp = await client.messages.create(model=MODEL, max_tokens=12000, output_config={"effort": "medium"},
                                                tools=tools, messages=messages)
            text = _text(resp)
            for blk in resp.content:   # 실제로 던진 검색어 수집 (직접 호출 + 코드 실행 내부 호출)
                if blk.type == "server_tool_use":
                    inp = getattr(blk, "input", {}) or {}
                    if blk.name == "web_search" and inp.get("query"):
                        queries.append(str(inp["query"]))
                    elif blk.name == "code_execution" and inp.get("code"):
                        queries += re.findall(r'"query"\s*:\s*"([^"]+)"', str(inp["code"]))
            if resp.stop_reason != "pause_turn":
                break
            messages.append({"role": "assistant", "content": resp.content})
        queries = list(dict.fromkeys(q.strip() for q in queries if q.strip()))
        data = _extract_json(text) or {}
        meta = {"queries": queries, "planned": planned, **({"plan_error": plan_err} if plan_err else {})}
        if not data.get("stories"):
            return {"stories": [], "fallback": True, "reason": f"parse 실패 (stop={resp.stop_reason}, text={text[-160:]!r})", **meta}
        stories = []
        for s in data.get("stories", [])[:3]:
            url = str(s.get("url", ""))
            if not url.startswith("http"):
                continue
            stories.append({"title": str(s.get("title", ""))[:80], "source": str(s.get("source", ""))[:40], "url": url,
                            "summary": str(s.get("summary", ""))[:300], "match_points": [str(x)[:80] for x in (s.get("match_points") or [])][:3],
                            "similarity": int(s.get("similarity", 0) or 0), "hit": str(s.get("hit", ""))[:120]})
        if not stories:
            return {"stories": [], "fallback": True, "reason": "검색 결과 없음", **meta}
        return {"stories": stories, "searched": True, **meta,
                "basis": {"attachment": ATTACH_KO.get(fun.persona.get("attachment") or "", None), "ending": ENDING_KO.get(fun.persona.get("ending") or "", None)}}
    except Exception as e:  # noqa: BLE001
        return {"stories": [], "fallback": True, "reason": str(e)[:200], "planned": planned}
