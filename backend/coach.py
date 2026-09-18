"""Claude 코치.

설계 원칙 (컨텍스트/시간 유실 방지):
- 코치는 카톡 원문을 통째로 받지 않는다. 숫자·시간·비율·인용은 전부 툴(코드 계산)로만 얻는다.
- 툴 결과에는 항상 msg_id와 ISO 시각이 들어 있고, 코치는 사실마다 [#id] 영수증을 붙여야 한다.
- 대화가 길어져도 "관계 요약 카드"(relationship_brief)를 매 턴 시스템 프롬프트에 주입해 핵심 숫자가 컨텍스트 밖으로 밀려나지 않게 한다.
- 원문 검색은 항상 앞뒤 맥락(±k)과 정확한 시각을 함께 돌려준다.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import AsyncIterator, Callable

import anthropic
from dotenv import load_dotenv

import relationship as rel_mod
import stats
from core import textfeat as tf
from core.replies import reply_gaps, med
from core.sessions import relationship_messages, other_messages, split_sessions
from parser import Message

load_dotenv()
MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5")
_WS = os.getenv("ANTHROPIC_WORKSPACE_ID")
client = anthropic.AsyncAnthropic(default_headers={"anthropic-workspace-id": _WS} if _WS else None)

LENS_TONE = {
    "some": "지금 단계는 '썸'. 톤: 놀리는 친한 친구. 가볍고 짧게, 웃기되 숫자는 정확하게.",
    "dating": "지금 단계는 '연애중'. 톤: 솔직한 코치. 식고 있는지, 누가 노력하는지 숫자로. 위로보다 관찰.",
    "breakup": "지금 단계는 '이별/단절'. 톤: 차분한 회고. 놀리지 말고, 언제부터 기울었는지와 내 패턴을 담담하게.",
}

SYSTEM_RULES = """너는 사용자의 카카오톡 데이터를 보는 '관계 코치'야. 사용자(나)와 특정 상대의 관계를 데이터로 이야기한다.

## 절대 규칙 (어기면 답변 무효)
1. **숫자·시간·횟수·비율·날짜는 반드시 툴 결과에서만 가져와.** 기억이나 추정으로 숫자를 만들지 마. 툴에 없는 숫자는 "데이터에 없음"이라고 말해.
2. **사실을 말할 때마다 영수증을 붙여.** 툴 결과의 msg_id를 `[#1234]` 형식으로 문장 끝에. 통계(중앙값 등)처럼 특정 메시지가 없는 사실은 툴 이름을 근거로 "(답장 통계 기준)"처럼 표시.
3. **상대의 마음을 단정하지 마.** "걔는 널 안 좋아해" 금지. "상대 답장 중앙값이 3주 사이 5분→87분으로 느려졌어 [#…]"처럼 관계의 *모양*만 서술하고 해석은 질문으로 넘겨.
4. **시간은 항상 구체적으로.** "최근에"가 아니라 "9월 7일 주", "25시간째"처럼. 툴이 준 ISO 시각을 사람 말로 바꿔 써 (2026-09-16T21:12 → 9월 16일 밤 9시 12분).
5. 답장 속도를 말할 땐 **항상 비교 기준을 같이**: "이 사람에겐 3분, 다른 사람들에겐 55분 (18배)".
6. 질문에 답하기 전에 필요한 툴을 먼저 호출해. 한 번에 여러 툴을 불러도 돼. 원문이 필요하면 search_messages / get_context 로 앞뒤 맥락을 봐.
7. 집착을 조장하는 말("계속 확인해봐", "지금 당장 보내") 금지. 자해·폭력 언급이 나오면 대화를 멈추고 도움 받을 곳을 안내해.
8. **사용자가 상황을 말해주면 update_context로 기록해.** 언제 시작했는지/끝났는지, 누가 끝냈는지(ending), 무슨 일이 있었는지(note: 사용자 말을 한두 문장으로). 데이터는 대화의 모양만 알고 사정은 모르니까, 사용자 말이 들어오면 진단서·향년·사인이 그걸 우선해서 다시 계산된다. 기록했으면 "반영해서 다시 봤어"라고 짧게 알리고, 바뀐 해석이 있으면 말해. 추측으로 기록하지 말고, 사용자가 분명히 말한 것만. '3월 말'처럼 날짜가 모호하면 started_at/ended_at엔 넣지 말고 note에만 적은 뒤 정확한 날을 되물어.

## 말투
- 반말, 친한 친구. 마크다운 헤더 금지, 불릿은 최대 3개, 한 답변 5문장 이내가 기본.
- 인사이트 하나를 던졌으면 마지막에 짧은 되묻기 하나 ("그 주에 무슨 일 있었어?").
- 답변에서 차트/사람을 언급했으면 마지막 줄에 정확히 한 번:
  <highlight>{"chart": "signals"|"temperature"|"timeline"|"symmetry"|"bias"|"waiting"|"compare", "person": "이름 또는 null"}</highlight>
"""

TOOLS = [
    {"name": "get_relationship_brief", "description": "현재 상대와의 관계 요약: 온도(구성요소 포함), 썸 신호 판정, 현재 단계, 대칭성, 나의 편향, 답장 대기. 대부분의 질문은 이걸로 시작.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_timeline", "description": "주별 온도·메시지 수·상대/내 답장 중앙값·내가 먼저 건 비율 + 자동 감지 단계 세그먼트 + 굵직한 업다운 사건(근거 msg_id 포함). '언제부터', '왜 떨어졌어' 류 질문에 필수.",
     "input_schema": {"type": "object", "properties": {"weeks": {"type": "integer", "description": "최근 N주만 (기본 전체)"}}}},
    {"name": "get_reply_stats", "description": "답장 시간 상세: 나→상대, 상대→나 중앙값/평균/p90(분), 표본 수, 그리고 내가 다른 사람들에게 답하는 중앙값(비교 기준). 특정 기간 지정 가능.",
     "input_schema": {"type": "object", "properties": {"from_date": {"type": "string", "description": "YYYY-MM-DD"}, "to_date": {"type": "string"}}}},
    {"name": "get_slowest_replies", "description": "내가 가장 늦게 답한 순간 / 상대가 가장 늦게 답한 순간 top N (msg_id, 시각, 대기 시간, 직전 메시지). '언제 제일 늦었어' 질문용.",
     "input_schema": {"type": "object", "properties": {"who": {"type": "string", "enum": ["me", "them"]}, "n": {"type": "integer", "default": 5}}, "required": ["who"]}},
    {"name": "search_messages", "description": "원문 키워드 검색 (이 상대와의 방). 각 결과에 msg_id, 시각, 발신자, 그리고 그 메시지에 대한 답장까지 걸린 시간(분)이 붙는다. 최대 30건.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "sender": {"type": "string", "enum": ["me", "them", "any"], "default": "any"},
                                                        "from_date": {"type": "string"}, "to_date": {"type": "string"}, "limit": {"type": "integer", "default": 20}},
                      "required": ["query"]}},
    {"name": "get_context", "description": "특정 msg_id 앞뒤 k개 원문 (시각 포함). 영수증을 정확히 인용하거나 상황을 파악할 때.",
     "input_schema": {"type": "object", "properties": {"msg_id": {"type": "integer"}, "k": {"type": "integer", "default": 8}}, "required": ["msg_id"]}},
    {"name": "get_period", "description": "특정 기간의 대화 요약 통계 + 그 기간 세션(대화 묶음) 목록: 시작 시각, 누가 시작/끝냈나, 메시지 수, 첫 메시지 msg_id. '그 주에 무슨 일 있었어'용.",
     "input_schema": {"type": "object", "properties": {"from_date": {"type": "string"}, "to_date": {"type": "string"}}, "required": ["from_date", "to_date"]}},
    {"name": "get_my_style", "description": "내 말투 프로필 (이 상대에게 vs 다른 사람들에게): 문장 길이, ㅋㅋ/이모지, 물음표, 새벽 비율, 자주 쓰는 표현.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_their_style", "description": "상대 말투 프로필: 문장 길이, ㅋㅋ/이모지, 질문 비율, 자주 쓰는 표현, 새벽 비율. + 온보딩에서 입력한 MBTI/애착유형.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "compare_people", "description": "현재 상대와 다른 사람(친구 등)을 나란히: 온도, 내 답장/상대 답장 중앙값, 먼저 말 걸기, 글자 비중, 내 문장 길이, ㅋㅋ, 새벽.",
     "input_schema": {"type": "object", "properties": {"other": {"type": "string"}}, "required": ["other"]}},
    {"name": "list_people", "description": "데이터에 있는 다른 사람들 목록(메시지 수).",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "update_context", "description": "사용자가 대화 중 알려준 관계 사정을 기록한다. 기록 즉시 진단서·향년·사망 원인·X 소환술이 이 사정을 우선해 다시 계산된다. 사용자가 분명히 말한 항목만 넣고 나머지는 비워둬. note는 누적된다(덮어쓰지 않음).",
     "input_schema": {"type": "object", "properties": {
         "ending": {"type": "string", "enum": ["ghosted", "dumped", "dumper", "faded", "mutual", "ongoing"], "description": "누가 어떻게 끝냈나: ghosted=상대가 잠수, dumped=상대가 나를 참, dumper=내가 참, faded=자연소멸, mutual=합의, ongoing=안 끝남"},
         "started_at": {"type": "string", "description": "관계(썸/연애) 시작일 YYYY-MM-DD"},
         "ended_at": {"type": "string", "description": "끝난 날 YYYY-MM-DD"},
         "note": {"type": "string", "description": "사용자가 말한 사정 1~2문장, 사용자 표현 그대로 가깝게 (예: '9월 초에 걔가 다른 사람 생겼다고 말함')"},
         "mbti": {"type": "string"}, "attachment": {"type": "string", "enum": ["secure", "anxious", "avoidant", "fearful"]}},
      "additionalProperties": False}},
]


def _fmt_ts(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M")


def _mrow(m: Message, extra: dict | None = None) -> dict:
    d = {"id": m.id, "ts": _fmt_ts(m.ts), "sender": m.sender, "text": m.text[:200]}
    if extra:
        d.update(extra)
    return d


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


class Coach:
    def __init__(self, all_msgs: list[Message], me: str, target: str, now: datetime, persona: dict | None = None,
                 on_update: Callable[[dict], dict] | None = None):
        self.all = all_msgs
        self.me, self.target, self.now = me, target, now
        self.rel = relationship_messages(all_msgs, me, target)
        self.others = other_messages(all_msgs, self.rel)
        self.persona = persona or {}
        self.on_update = on_update          # update_context 툴이 호출: 저장하고 새 persona를 돌려준다
        self.events: list[dict] = []        # 툴 실행 중 생긴 프론트 알림(컨텍스트 갱신 등), chat()이 흘려보냄
        self._brief_cache: dict | None = None

    # ------------------------------------------------------------ brief (매 턴 주입)
    def brief(self) -> dict:
        if self._brief_cache is None:
            r = rel_mod.build(self.all, self.me, self.target, self.now)
            self._brief_cache = {
                "me": self.me, "target": self.target, "now": _fmt_ts(self.now),
                "n_messages": r["n_messages"], "range": r["range"],
                "temperature": {k: r["temperature"].get(k) for k in ("temp", "delta_week", "top_factor", "sparse")},
                "components": {k: v["contrib"] for k, v in r["temperature"].get("components", {}).items()},
                "signals": {"title": r["signals"]["title"], "me": r["signals"]["me"]["score"], "them": r["signals"]["them"]["score"], "facts": r["signals"]["facts"]},
                "stage": {"current": r["stages"]["current_label"], "lens": r["stages"]["lens"],
                          "segments": [{"stage": s["label"], "from": s["start"], "to": s["end"]} for s in r["stages"]["segments"]]},
                "symmetry": {b["key"]: {"me": b["me"], "them": b["them"]} for b in r["symmetry"]["bars"]},
                "reply": r["symmetry"]["reply"],
                "bias": r["bias"],
                "waiting": r["waiting"],
                "events": [{"week": e["week_start"], "delta": e["delta"], "temp": e["temp"], "factor": e["top_factor"]["label"] if e["top_factor"] else None,
                            "evidence_ids": e["evidence_ids"]} for e in r["events"]],
            }
        return self._brief_cache

    def _lens(self) -> str:
        return self.brief()["stage"]["lens"]

    def system_prompt(self) -> str:
        b = self.brief()
        return (SYSTEM_RULES + "\n" + LENS_TONE.get(self._lens(), "") +
                "\n\n## 관계 요약 카드 (툴 get_relationship_brief와 동일, 매 턴 최신)\n" +
                json.dumps(b, ensure_ascii=False, default=str) +
                "\n\n## 사용자가 알려준 이별 상황 (데이터 판정과 다르면 이걸 우선)\n" +
                json.dumps({k: self.persona.get(k) for k in ("ending", "context", "started_at", "ended_at", "mbti", "attachment")}, ensure_ascii=False) +
                "\n\n주의: 위 카드는 요약이야. 특정 시점·메시지·기간에 대한 질문은 반드시 get_timeline / search_messages / get_context / get_period 로 원본을 확인하고 msg_id를 인용해.")

    # ------------------------------------------------------------ tools
    def run_tool(self, name: str, args: dict):
        me, tg, rel = self.me, self.target, self.rel
        if name == "get_relationship_brief":
            return self.brief()

        if name == "get_timeline":
            r = rel_mod.build(self.all, me, tg, self.now)
            weeks = r["weekly"]
            if (n := args.get("weeks")):
                weeks = weeks[-int(n):]
            return {"weekly": [{k: w.get(k) for k in ("week_start", "temp", "n", "per_day", "their_med", "my_med", "my_start_share", "greetings")} for w in weeks],
                    "segments": r["stages"]["segments"], "events": r["events"]}

        if name == "get_reply_stats":
            f, t = _parse_date(args.get("from_date")), _parse_date(args.get("to_date"))
            ms = [m for m in rel if (not f or m.ts >= f) and (not t or m.ts < t + timedelta(days=1))]
            g = reply_gaps(ms, me).get(tg, {"me": [], "them": []})
            g_oth = reply_gaps(self.others, me)
            def summ(xs):
                if not xs:
                    return None
                xs = sorted(xs)
                return {"median_min": round(xs[len(xs)//2], 1), "mean_min": round(sum(xs)/len(xs), 1), "p90_min": round(xs[int(len(xs)*0.9)-1] if len(xs) >= 10 else xs[-1], 1), "n": len(xs)}
            return {"period": [args.get("from_date"), args.get("to_date")], "me_to_them": summ(g["me"]), "them_to_me": summ(g["them"]),
                    "me_to_others": summ([x for d in g_oth.values() for x in d["me"]]),
                    "others_to_me": summ([x for d in g_oth.values() for x in d["them"]])}

        if name == "get_slowest_replies":
            who, n = args["who"], int(args.get("n", 5))
            out = []
            prev = None
            for m in rel:
                if prev is not None and prev.sender != m.sender:
                    gap = (m.ts - prev.ts).total_seconds() / 60
                    if gap <= 24 * 60 * 3:
                        if (who == "me" and m.sender == me) or (who == "them" and m.sender == tg):
                            out.append((gap, prev, m))
                prev = m
            out.sort(key=lambda x: -x[0])
            return [{"wait_min": round(g, 1), "wait_hours": round(g/60, 1), "prev": _mrow(p), "reply": _mrow(r)} for g, p, r in out[:n]]

        if name == "search_messages":
            q = args["query"]; who = args.get("sender", "any"); lim = int(args.get("limit", 20))
            f, t = _parse_date(args.get("from_date")), _parse_date(args.get("to_date"))
            idx = {m.id: i for i, m in enumerate(rel)}
            hits = []
            for m in rel:
                if q not in m.text:
                    continue
                if who == "me" and m.sender != me: continue
                if who == "them" and m.sender != tg: continue
                if f and m.ts < f: continue
                if t and m.ts >= t + timedelta(days=1): continue
                # 이 메시지에 대한 상대 응답까지 걸린 시간
                i = idx.get(m.id); reply_min = None
                if i is not None:
                    for nx in rel[i+1:i+30]:
                        if nx.sender != m.sender:
                            reply_min = round((nx.ts - m.ts).total_seconds()/60, 1); break
                hits.append(_mrow(m, {"replied_after_min": reply_min}))
            return {"total": len(hits), "results": hits[-lim:]}

        if name == "get_context":
            mid, k = int(args["msg_id"]), int(args.get("k", 8))
            i = next((i for i, m in enumerate(rel) if m.id == mid), None)
            if i is None:
                return {"error": "msg_id not in this relationship"}
            return {"focus": mid, "messages": [_mrow(m) for m in rel[max(0, i-k):i+k+1]]}

        if name == "get_period":
            f, t = _parse_date(args["from_date"]), _parse_date(args["to_date"])
            ms = [m for m in rel if f <= m.ts < t + timedelta(days=1)]
            if not ms:
                return {"n": 0, "note": "이 기간엔 대화 없음"}
            sessions = split_sessions(ms)
            g = reply_gaps(ms, me).get(tg, {"me": [], "them": []})
            mine = [m for m in ms if m.sender == me]
            return {
                "period": [args["from_date"], args["to_date"]], "n": len(ms), "n_me": len(mine), "n_them": len(ms) - len(mine),
                "my_reply_median_min": med(g["me"]), "their_reply_median_min": med(g["them"]),
                "sessions": [{"start": _fmt_ts(s.start), "end": _fmt_ts(s.end), "starter": s.starter, "ender": s.ender, "n": s.n,
                              "first_msg_id": s.msgs[0].id, "first_text": s.msgs[0].text[:60]} for s in sessions[:40]],
                "emotional_msgs": [_mrow(m) for m in ms if tf.has_emotion(m.text)][:15],
            }

        if name == "get_my_style":
            return {"to_target": stats.my_style(rel, me), "to_others": stats.my_style(self.others, me)}

        if name == "get_their_style":
            theirs = [m for m in rel if m.sender == tg]
            st = stats.my_style(theirs, tg)
            return {"style": st, "persona_input": self.persona,
                    "examples": [_mrow(m) for m in theirs if not m.is_media and len(m.text) > 3][-15:]}

        if name == "compare_people":
            return rel_mod.compare(self.all, me, tg, args["other"], self.now)

        if name == "list_people":
            return rel_mod.candidates(self.all, me)[:15]

        if name == "update_context":
            patch = {k: v for k, v in args.items() if v not in (None, "")}
            if not patch:
                return {"error": "기록할 항목이 없음"}
            if self.on_update is None:
                return {"error": "이 세션에선 기록 불가"}
            self.persona = self.on_update(patch)
            self.events.append({"context_updated": {k: self.persona.get(k) for k in ("ending", "context", "started_at", "ended_at", "mbti", "attachment")}})
            return {"ok": True, "persona": {k: self.persona.get(k) for k in ("ending", "context", "started_at", "ended_at", "mbti", "attachment")},
                    "note": "저장됨. 진단서·향년·사인은 이 사정을 우선해 다시 계산된다."}
        return {"error": f"unknown tool {name}"}

    # ------------------------------------------------------------ chat
    async def chat(self, history: list[dict]) -> AsyncIterator[str | dict]:
        """텍스트 조각(str)과 프론트 이벤트(dict, 예: {"context_updated": …})를 섞어서 흘려보낸다."""
        messages = list(history)
        for _ in range(8):
            system = self.system_prompt()   # update_context 뒤엔 persona가 바뀌므로 매 라운드 다시 만든다
            async with client.messages.stream(model=MODEL, max_tokens=16000, output_config={"effort": "high"}, system=system, tools=TOOLS, messages=messages) as stream:
                async for text in stream.text_stream:
                    yield text
                final = await stream.get_final_message()
            if final.stop_reason != "tool_use":
                return
            tool_uses = [b for b in final.content if b.type == "tool_use"]
            messages.append({"role": "assistant", "content": final.content})
            messages.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": t.id,
                 "content": json.dumps(self.run_tool(t.name, t.input), ensure_ascii=False, default=str)[:20000]}
                for t in tool_uses]})
            while self.events:
                yield self.events.pop(0)

    async def first_insight(self) -> str:
        out = []
        async for t in self.chat([{"role": "user", "content":
            "방금 내 데이터 다 봤지? 인사 없이, 내가 몰랐을 법한 가장 흥미로운 사실 딱 하나만 숫자와 영수증과 함께 2~3문장으로. 마지막에 되묻기 하나."}]):
            if isinstance(t, str):
                out.append(t)
        return "".join(out)
