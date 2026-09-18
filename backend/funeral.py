"""장례식 전용 LLM 기능: X 소환술(상대 말투 복제), 진정성 진단서, 저주 부적.
전부 '실패하면 템플릿 폴백' — 키가 없어도 데모는 돌아간다.
"""
from __future__ import annotations

import json
import os
import random
import re
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
    if m < 1:
        return "1분 이내"
    return f"{m:.0f}분" if m < 60 else (f"{m/60:.1f}시간" if m < 1440 else f"{m/1440:.1f}일")


class Funeral:
    def __init__(self, all_msgs: list[Message], me: str, target: str, now: datetime, persona: dict | None):
        self.all, self.me, self.target, self.now = all_msgs, me, target, now
        self.persona = persona or {}
        self.rel = relationship_messages(all_msgs, me, target)
        self.brief = rel_mod.build(all_msgs, me, target, now)

    def context_line(self) -> str:
        p = self.persona
        bits = []
        if p.get("ending"):
            bits.append(f"이별 방식(사용자 진술): {ENDING_KO.get(p['ending'], p['ending'])}")
        if p.get("ended_at"):
            bits.append(f"헤어진 날: {p['ended_at']}")
        if p.get("context"):
            bits.append(f"사용자가 설명한 상황: {p['context'][:400]}")
        return "\n".join(bits) if bits else "(사용자가 추가로 알려준 이별 상황 없음)"

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
- 관계 현재 상태(데이터): {b['stages']['current_label']}, 최근 상대 답장 중앙값 {_fmt_min(b['symmetry']['reply']['their_median_min'])}
- {self.context_line()}  ← 데이터와 다르면 이 사용자 진술을 우선해. (예: 데이터는 '썸'이지만 사용자가 '잠수로 끝났다'면 이미 끝난 관계로 연기)

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

[사용자가 알려준 이별 상황]
{self.context_line()}

규칙: 5~6문장, 반말 아닌 부드러운 존댓말("~에요"), 숫자는 위 사실에서만 인용(최소 2개), 상대의 마음을 단정하지 말고 관계의 모양만 말해, 사용자가 알려준 이별 상황이 있으면 그 맥락에 맞춰(데이터 판정과 달라도 사용자 진술 우선), 마지막 문장은 놓아주라는 말로 끝내. 이모지 1개까지. 제목 없이 본문만."""
        try:
            resp = await client.messages.create(model=MODEL, max_tokens=6000, output_config={"effort": "medium"}, messages=[{"role": "user", "content": prompt}])
            return {"text": "".join(b.text for b in resp.content if b.type == "text").strip()}
        except Exception:  # noqa: BLE001
            return {"text": self.template_eulogy(), "fallback": True}

    # ------------------------------------------------------------ 저주 부적 (애착유형별 사자성어 + 맞춤 한 줄)
    async def curse(self) -> dict:
        b = self.brief; r = b["symmetry"]["reply"]; w = b["waiting"]
        attach = self.persona.get("attachment")
        hanja, reading, meaning = AMULETS.get(attach, AMULETS[None])[0]
        st = stats.my_style([m for m in self.rel if m.sender == self.target], self.target)
        prompt = f"""부적에 이미 큰 글씨로 '{hanja.replace(chr(10), ' ')}'({reading}: {meaning})이 박혀 있어. 그 아래 작게 들어갈 '맞춤 저주 한 줄'을 써.
'{self.target}'의 카톡 패턴: 답장 중앙값 {_fmt_min(r['their_median_min'])}, 자주 쓰는 말 {', '.join(w_ for w_, _ in st.get('top_words', [])[:6])}, 평균 {st.get('avg_len')}자 단답{(', 마지막 메시지에 %s시간째 미응답' % w['age_hours']) if w else ''}.
{self.context_line()}
조건: 한 줄(20자 이내), 잔인/신체 위해/혐오 금지, 유치하고 소심하게 웃긴 저주, 상대의 실제 패턴 하나를 반드시 넣기. 예: "잘자 보낸 밤마다 와이파이 끊겨라". 문구만 출력."""
        base = {"hanja": hanja, "reading": reading, "meaning": meaning, "attachment": attach,
                "attachment_label": ATTACH_KO.get(attach or "", "유형 미상")}
        try:
            resp = await client.messages.create(model=MODEL, max_tokens=4000, output_config={"effort": "low"},
                                                messages=[{"role": "user", "content": prompt}])
            text = "".join(b_.text for b_ in resp.content if b_.type == "text").strip().strip('"')
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            line = lines[-1] if lines else random.choice(CURSES).replace("\n", " ")
            return {**base, "line": line[:40], "text": line[:40]}
        except Exception:  # noqa: BLE001
            line = random.choice(CURSES).replace("\n", " ")
            return {**base, "line": line, "text": line, "fallback": True}


# ------------------------------------------------------------ 레전드 썰 매칭 (웹 검색)
LEGEND_DOMAINS = ["pann.nate.com", "gall.dcinside.com", "m.dcinside.com", "theqoo.net", "instiz.net", "fmkorea.com",
                  "teamblind.com", "everytime.kr", "ppomppu.co.kr", "clien.net", "82cook.com", "bobaedream.co.kr", "orbi.kr", "dogdrip.net"]
LEGEND_SCHEMA_HINT = """{"stories": [{"title": "...", "source": "네이트판 톡 / 디시 연애갤 / 더쿠 ...", "url": "https://...",
  "summary": "글의 상황을 내 말로 2문장 요약 (원문 복사 금지)", "match_points": ["내 데이터와 겹치는 점 1", "겹치는 점 2"],
  "similarity": 0~100 정수, "hit": "현타 포인트 한 문장"}]}"""


class _LegendMixin:
    pass


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


async def legends_for(fun: "Funeral") -> dict:
    """내 관계 데이터 + 사용자 진술을 검색 쿼리로 바꿔 커뮤니티 썰을 실시간 검색·매칭."""
    b = fun.brief; r = b["symmetry"]["reply"]; w = b["waiting"]; c = b.get("causes") or {}
    facts = [
        f"관계 단계 흐름: {' → '.join(s['label'] for s in b['stages']['segments'])}",
        f"상대 답장 중앙값 {_fmt_min(r['their_median_min'])}, 내 답장 중앙값 {_fmt_min(r['my_median_min'])}",
        f"나는 이 사람에게 다른 사람보다 {b['bias']['reply_speed']['times_faster']}배 빨리 답함",
    ]
    if w:
        facts.append(f"상대 마지막 메시지 “{w['text'][:40]}” 에 {w['age_hours']}시간째 무응답")
    persona = ", ".join(x for x in [fun.persona.get("mbti"), ATTACH_KO.get(fun.persona.get("attachment") or "")] if x)
    prompt = f"""아래는 사용자의 카톡 데이터로 계산한 관계 사실과, 사용자가 직접 알려준 이별 상황이야.
이와 **비슷한 상황의 실제 커뮤니티 썰**을 웹에서 찾아서 2~3개 골라줘. 네이트판 톡, 디시 연애갤, 더쿠, 인스티즈, 에펨코리아, 블라인드 같은 곳.

[데이터 사실]
{chr(10).join('- ' + x for x in facts)}
- 상대 성향(사용자 입력): {persona or '미입력'}
- {fun.context_line()}

[규칙]
1. web_search로 2~4번 검색해. 검색어는 한국어로, 상황 키워드 조합 (예: "회피형 잠수 이별 썰", "읽씹 후 잠수 네이트판", "연락 뜸해지다가 잠수").
2. 실제로 존재하는 글만. URL은 검색 결과에 있던 것 그대로. 지어내지 마.
3. 요약은 원문을 복사하지 말고 상황만 내 말로 2문장. 실명·연락처 등 개인정보 제외.
4. 각 썰마다 사용자 데이터와 겹치는 점을 구체적으로 (예: "상대 답장은 빨랐는데 어느 날 갑자기 끊김").
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
            text = "".join(blk.text for blk in resp.content if blk.type == "text")
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
        if not data.get("stories"):
            return {"stories": [], "fallback": True, "reason": f"parse 실패 (stop={resp.stop_reason}, text={text[-160:]!r})", "queries": queries}
        stories = []
        for s in data.get("stories", [])[:3]:
            url = str(s.get("url", ""))
            if not url.startswith("http"):
                continue
            stories.append({"title": str(s.get("title", ""))[:80], "source": str(s.get("source", ""))[:40], "url": url,
                            "summary": str(s.get("summary", ""))[:300], "match_points": [str(x)[:80] for x in (s.get("match_points") or [])][:3],
                            "similarity": int(s.get("similarity", 0) or 0), "hit": str(s.get("hit", ""))[:120]})
        if not stories:
            return {"stories": [], "fallback": True, "reason": "검색 결과 없음", "queries": queries}
        return {"stories": stories, "searched": True, "queries": queries,
                "basis": {"attachment": ATTACH_KO.get(fun.persona.get("attachment") or "", None), "ending": ENDING_KO.get(fun.persona.get("ending") or "", None)}}
    except Exception as e:  # noqa: BLE001
        return {"stories": [], "fallback": True, "reason": str(e)[:200]}
