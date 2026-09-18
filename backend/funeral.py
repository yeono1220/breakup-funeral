"""장례식 전용 LLM 기능: X 소환술(상대 말투 복제), 진정성 진단서, 저주 부적.
전부 '실패하면 템플릿 폴백' — 키가 없어도 데모는 돌아간다.
"""
from __future__ import annotations

import os
import random
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
CANNED_REPLIES = ["ㅇㅇ 근데 그건 네 생각이고", "바쁘다니까 자꾸", "미안한데 나 진짜 변한 거 없어", "그때도 말했잖아 ㅎㅎ",
                  "굳이 지금 이걸 물어봐야 돼?", "너 또 이런다 진짜", "나중에 연락할게"]
CURSES = ["읽씹하던 그 손가락,\n앞으로 오타만 나거라", "너의 모든 소개팅에\n어색한 침묵이 깃들기를", "새 연애 3일 만에\n전 애인 얘기 튀어나와라",
          "너의 인스타 스토리\n조회수 평생 한 자리수", "'바빴어'라는 변명,\n네 인생 최고 히트작 되거라"]


_META = ("시뮬레이터", "simulat", "역할", "샘플", "사용자", "assistant", "respond", "keep it", "per the")


def _clean_reply(text: str) -> str:
    """모델이 추론을 본문에 섞어 내놓아도 실제 카톡 한 줄만 남긴다."""
    lines = [l.strip().strip('"“”') for l in text.splitlines() if l.strip()]
    lines = [l for l in lines if not any(k in l.lower() for k in _META)]
    if not lines:
        return ""
    reply = lines[-1]
    return reply[:80]


def _fmt_min(m: float | None) -> str:
    if m is None:
        return "–"
    return f"{m:.0f}분" if m < 60 else (f"{m/60:.1f}시간" if m < 1440 else f"{m/1440:.1f}일")


class Funeral:
    def __init__(self, all_msgs: list[Message], me: str, target: str, now: datetime, persona: dict | None):
        self.all, self.me, self.target, self.now = all_msgs, me, target, now
        self.persona = persona or {}
        self.rel = relationship_messages(all_msgs, me, target)
        self.brief = rel_mod.build(all_msgs, me, target, now)

    # ------------------------------------------------------------ 상대 말투 자료
    def their_style_pack(self) -> dict:
        theirs = [m for m in self.rel if m.sender == self.target and not m.is_media and len(m.text.strip()) > 1]
        st = stats.my_style(theirs, self.target)
        # 상황별 예시: 내가 감정/질문을 던졌을 때 상대가 어떻게 받았나 (페어)
        pairs = []
        for i in range(1, len(self.rel)):
            a, b = self.rel[i - 1], self.rel[i]
            if a.sender == self.me and b.sender == self.target and not b.is_media and len(pairs) < 40:
                pairs.append((a.text[:80], b.text[:120]))
        return {"style": st, "examples": [m.text for m in theirs[-40:]], "pairs": pairs[-25:]}

    def summon_system(self) -> str:
        p = self.their_style_pack()
        st = p["style"]
        persona_line = ", ".join(x for x in [self.persona.get("mbti"), ATTACH_KO.get(self.persona.get("attachment") or "")] if x)
        b = self.brief
        return f"""너는 사용자의 전 연인/썸 상대 '{self.target}'의 카카오톡 말투를 그대로 복제한 시뮬레이터야. 사용자가 미련 섞인 말을 던지면 '{self.target}'이라면 실제로 보냈을 법한 답을 한다.

## 이 사람의 실제 말투 (데이터)
- 평균 {st.get('avg_len')}자, 중앙값 {st.get('median_len')}자. 이보다 길게 쓰지 마.
- ㅋㅋ 사용률 {st.get('kkk_ratio')}, 물음표 {st.get('question_ratio')}, 느낌표 {st.get('exclaim_ratio')}, 이모지 {st.get('emoji_ratio')}. 이 비율을 벗어나지 마.
- 자주 쓰는 표현: {', '.join(w for w, _ in st.get('top_words', [])[:12])}
- 성격 힌트(사용자 입력): {persona_line or '없음'}
- 관계 현재 상태: {b['stages']['current_label']}, 최근 상대 답장 중앙값 {_fmt_min(b['symmetry']['reply']['their_median_min'])}

## 실제로 보낸 메시지 샘플 (이 톤 그대로)
{chr(10).join('- ' + e for e in p['examples'][-25:])}

## 내가 말했을 때 → 이 사람의 실제 반응 (페어)
{chr(10).join(f'- 나: {a} → {self.target}: {b_}' for a, b_ in p['pairs'][-15:])}

## 규칙
1. 한 번에 한 메시지, 실제 카톡처럼 짧게. 위 샘플보다 다정하거나 설명적이면 실패.
2. 이 사람은 이미 멀어진 상태다. 사용자를 붙잡지 말고, 실제 패턴대로 미지근하게/짧게/회피적으로 답해. 그게 사용자를 위한 '현실 직시'다.
3. AI 티 금지: 완벽한 맞춤법·존댓말 전환·"~인 것 같아요!"·과한 공감 문구 금지. 샘플의 띄어쓰기·어미 습관을 따라 해.
4. 절대 실제 사람인 척 사용자를 속이지 마 — 사용자는 시뮬레이터임을 알고 있다. 자해·위험 신호가 보이면 시뮬을 멈추고 "이건 시뮬레이터야. 힘들면 1393(자살예방상담)에 전화해줘"라고 말해.
5. 출력은 **딱 한 줄, 메시지 본문만.** 따옴표·설명·생각 과정·영어 절대 금지. 첫 글자부터 카톡 메시지여야 한다."""

    async def summon(self, messages: list[dict]) -> dict:
        try:
            resp = await client.messages.create(model=MODEL, max_tokens=4000, output_config={"effort": "medium"}, system=self.summon_system(),
                                                messages=[{"role": m["role"], "content": m["content"]} for m in messages if m.get("content")])
            text = "".join(b.text for b in resp.content if b.type == "text")
            reply = _clean_reply(text)
            return {"reply": reply or random.choice(CANNED_REPLIES)}
        except Exception:  # noqa: BLE001
            return {"reply": random.choice(CANNED_REPLIES), "fallback": True}

    # ------------------------------------------------------------ 진정성 진단서
    def _facts(self) -> str:
        b = self.brief
        r = b["symmetry"]["reply"]; bi = b["bias"]; w = b["waiting"]; sg = b["signals"]
        lines = [
            f"- 기간 {b['range'][0][:10]} ~ {b['range'][1][:10]}, 메시지 {b['n_messages']}개",
            f"- 단계 흐름: {' → '.join(s['label'] for s in b['stages']['segments'])} (현재 {b['stages']['current_label']})",
            f"- 온도 {b['temperature'].get('temp')}°, 주간 변화 {b['temperature'].get('delta_week')}",
            f"- 내 답장 중앙값 {_fmt_min(r['my_median_min'])} / 상대 {_fmt_min(r['their_median_min'])}",
            f"- 나는 이 사람에게 다른 사람보다 {bi['reply_speed']['times_faster']}배 빨리 답함 ({_fmt_min(bi['reply_speed']['to_target_min'])} vs {_fmt_min(bi['reply_speed']['to_others_min'])})",
            f"- 썸 신호 판정: {sg['title']} (나 {sg['me']['score']} / 상대 {sg['them']['score']})",
        ]
        if w:
            lines.append(f"- 상대 마지막 메시지 “{w['text']}” 에 {w['age_hours']}시간째 내가 답 안 함 (평소 {_fmt_min(w['usual_reply_min'])})")
        for e in b["events"][:4]:
            lines.append(f"- {e['week_start']} 주: 온도 {e['delta']:+}° ({e['top_factor']['label'] if e['top_factor'] else ''})")
        return "\n".join(lines)

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

    async def eulogy(self) -> dict:
        prompt = f"""아래는 사용자와 '{self.target}'의 카톡 데이터에서 코드로 계산한 사실이야. 이 사실만 근거로 '진정성 있는 팩폭 위로 진단서'를 써.

{self._facts()}

규칙: 5~6문장, 반말 아닌 부드러운 존댓말("~에요"), 숫자는 위 사실에서만 인용(최소 2개), 상대의 마음을 단정하지 말고 관계의 모양만 말해, 마지막 문장은 놓아주라는 말로 끝내. 이모지 1개까지. 제목 없이 본문만."""
        try:
            resp = await client.messages.create(model=MODEL, max_tokens=6000, output_config={"effort": "medium"}, messages=[{"role": "user", "content": prompt}])
            return {"text": "".join(b.text for b in resp.content if b.type == "text").strip()}
        except Exception:  # noqa: BLE001
            return {"text": self.template_eulogy(), "fallback": True}

    # ------------------------------------------------------------ 저주 부적
    async def curse(self) -> dict:
        b = self.brief; r = b["symmetry"]["reply"]; w = b["waiting"]
        st = stats.my_style([m for m in self.rel if m.sender == self.target], self.target)
        prompt = f"""'{self.target}'의 카톡 패턴으로 웃긴 '저주 부적' 문구를 하나 써. 두 줄, 각 줄 12자 이내, 줄바꿈 하나. 잔인/신체 위해/혐오 금지, 유치하고 귀엽게 소심한 저주.
패턴: 답장 중앙값 {_fmt_min(r['their_median_min'])}, 자주 쓰는 말 {', '.join(w_ for w_, _ in st.get('top_words', [])[:6])}, 평균 {st.get('avg_len')}자 단답{(', 마지막 메시지에 %s시간째 미응답' % w['age_hours']) if w else ''}.
예시 톤: "읽씹하던 그 손가락,\\n앞으로 오타만 나거라". 문구만 출력."""
        try:
            resp = await client.messages.create(model=MODEL, max_tokens=4000, output_config={"effort": "low"}, messages=[{"role": "user", "content": prompt}])
            text = "".join(b_.text for b_ in resp.content if b_.type == "text").strip().strip('"').replace("\\n", "\n")
            lines = [l.strip() for l in text.splitlines() if l.strip()][-2:]
            return {"text": "\n".join(lines) if lines else random.choice(CURSES)}
        except Exception:  # noqa: BLE001
            return {"text": random.choice(CURSES), "fallback": True}
