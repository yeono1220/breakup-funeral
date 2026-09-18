"""FastAPI 서버: 업로드/연결 → 통계 → 채팅(SSE) → 답장 초안."""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import db
import relationship
from core.causes import diagnose as diagnose_causes
from core.sessions import relationship_messages as _rel_msgs
import stats
from coach import Coach
from funeral import Funeral
from parser import parse_file_meta

app = FastAPI(title="kakao-coach")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

UPLOAD_DIR = Path(__file__).parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
_HL = re.compile(r"<highlight>(.*?)</highlight>", re.S)


def _con():
    return db.connect()


def _coach() -> Coach:
    con = _con()
    me, target = db.get_setting(con, "me"), db.get_setting(con, "target")
    if not me or not target:
        raise HTTPException(400, "먼저 /me, /target 으로 나와 상대를 설정해줘")
    return Coach(db.all_messages(con), me, target, db.now_ts(con), _persona_of(con, target))


# ---------------------------------------------------------------- ingest
@app.post("/upload")
async def upload(files: list[UploadFile] = File(...)):
    con = _con()
    added, rooms = 0, []
    for f in files:
        dest = UPLOAD_DIR / f.filename
        dest.write_bytes(await f.read())
        msgs, saved = parse_file_meta(dest)
        db.bump_saved_at(con, saved)
        added += db.insert_messages(con, msgs)
        rooms.append({"file": f.filename, "messages": len(msgs), "room": msgs[0].room if msgs else None,
                      "saved_at": saved.isoformat()})
    return {"added": added, "files": rooms, "senders": db.senders(con)[:20]}


@app.post("/load_sample")
async def load_sample():
    con = _con()
    db.clear(con)
    con.execute("DELETE FROM settings WHERE key IN ('saved_at','target')")
    con.commit()
    sample = Path(__file__).parent.parent / "sample"
    total = 0
    for p in sorted(sample.glob("*.txt")):
        msgs, saved = parse_file_meta(p)
        db.bump_saved_at(con, saved)
        total += db.insert_messages(con, msgs)
    return {"added": total, "senders": db.senders(con)[:20]}


class MeBody(BaseModel):
    me: str


@app.post("/me")
async def set_me(body: MeBody):
    db.set_setting(_con(), "me", body.me)
    return {"ok": True}


@app.get("/senders")
async def senders():
    con = _con()
    return {"senders": db.senders(con)[:20], "me": db.get_setting(con, "me")}


class TargetBody(BaseModel):
    target: str


@app.post("/target")
async def set_target(body: TargetBody):
    db.set_setting(_con(), "target", body.target)
    return {"ok": True}


@app.get("/targets")
async def targets():
    con = _con()
    me = db.get_setting(con, "me")
    if not me:
        raise HTTPException(400, "me not set")
    return {"me": me, "target": db.get_setting(con, "target"), "candidates": relationship.candidates(db.all_messages(con), me)[:20]}


ENDED = {"ghosted", "dumped", "dumper", "faded", "mutual"}   # 사용자가 "끝났다"고 알려준 상태
ENDING_LABEL = {"ghosted": "잠수·읽씹", "dumped": "차임", "dumper": "내가 끝냄", "faded": "자연소멸", "mutual": "합의 이별",
                "ongoing": "아직 안 끝남", None: None}


class PersonaBody(BaseModel):
    person: str
    mbti: str | None = None          # "ENFP" | None(모름)
    attachment: str | None = None    # secure | anxious | avoidant | fearful | None
    ending: str | None = None        # ghosted | dumped | dumper | faded | mutual | ongoing | None
    context: str | None = None       # 어떻게 끝났는지 자유 서술
    ended_at: str | None = None      # YYYY-MM-DD (선택)
    started_at: str | None = None    # YYYY-MM-DD 썸/관계 시작일 (선택) — 향년 계산 기준
    alias: bool = True               # 화면에서 가명 표시
    portrait: str | None = None      # data URL (사용자가 그린/올린 X 얼굴)
    note: str | None = None          # (구버전 호환)


def _persona_of(con, person: str) -> dict:
    cur = json.loads(db.get_setting(con, "persona", "{}") or "{}")
    p = cur.get(person) or {}
    if "alias" not in p:
        p["alias"] = p.get("note") == "alias" or not p.get("note")
    return p


@app.post("/persona")
async def set_persona(body: PersonaBody):
    con = _con()
    cur = json.loads(db.get_setting(con, "persona", "{}") or "{}")
    prev = cur.get(body.person) or {}
    incoming = {k: v for k, v in body.model_dump().items() if k != "person"}
    if incoming.get("portrait") is None and prev.get("portrait"):   # 초상화 미포함 요청이면 기존 값 유지
        incoming["portrait"] = prev["portrait"]
    cur[body.person] = incoming
    db.set_setting(con, "persona", json.dumps(cur, ensure_ascii=False))
    out = dict(incoming); out["portrait"] = bool(out.get("portrait"))
    return {"ok": True, "persona": out}


@app.get("/persona/{person}")
async def get_persona(person: str):
    p = _persona_of(_con(), person)
    return {"person": person, "mbti": p.get("mbti"), "attachment": p.get("attachment"), "ending": p.get("ending"),
            "context": p.get("context"), "ended_at": p.get("ended_at"), "started_at": p.get("started_at"), "alias": p.get("alias", True),
            "portrait": p.get("portrait"), "ending_label": ENDING_LABEL.get(p.get("ending"))}


@app.delete("/data")
async def clear_data():
    con = _con()
    db.clear(con)
    con.execute("DELETE FROM settings")
    con.commit()
    return {"ok": True}


# ---------------------------------------------------------------- relationship view
@app.get("/relationship/{person}")
async def relationship_view(person: str):
    con = _con()
    me = db.get_setting(con, "me")
    if not me:
        raise HTTPException(400, "me not set")
    r = relationship.build(db.all_messages(con), me, person, db.now_ts(con))
    p = _persona_of(con, person)
    ending = p.get("ending")
    # 사용자가 알려준 이별 컨텍스트가 데이터 판정을 덮어쓴다 (회피형 X = 데이터상 '썸'으로 보이는 경우 등)
    # 향년 시작점: 사용자가 찍은 시작일 > 데이터의 첫 썸/연애 구간 시작 > 첫 메시지
    first_warm = next((sg["start"] for sg in r["stages"]["segments"] if sg["stage"] in ("some", "dating")), None)
    r["user_context"] = {"ending": ending, "ending_label": ENDING_LABEL.get(ending), "context": p.get("context"),
                         "ended_at": p.get("ended_at"), "started_at": p.get("started_at"), "suggested_start": first_warm,
                         "overrides_stage": ending in ENDED}
    all_msgs = db.all_messages(con)
    r["causes"] = diagnose_causes(_rel_msgs(all_msgs, me, person), me, person, db.now_ts(con), r["user_context"])
    if ending in ENDED:
        r["stages"]["data_lens"] = r["stages"]["lens"]
        r["stages"]["data_label"] = r["stages"]["current_label"]
        r["stages"]["lens"] = "breakup"
        r["stages"]["current_stage"] = "ended"
        r["stages"]["current_label"] = f"이별 ({ENDING_LABEL[ending]})"
    return r


@app.get("/compare")
async def compare_people(a: str, b: str):
    con = _con()
    me = db.get_setting(con, "me")
    if not me:
        raise HTTPException(400, "me not set")
    return relationship.compare(db.all_messages(con), me, a, b, db.now_ts(con))


@app.get("/messages")
async def messages_by_ids(ids: str):
    con = _con()
    id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()][:50]
    return {"messages": [_mdict(m) for m in db.messages_by_ids(con, id_list)]}


@app.get("/messages/around/{msg_id}")
async def messages_around(msg_id: int, k: int = 10):
    return {"messages": [_mdict(m) for m in db.messages_around(_con(), msg_id, k)], "focus": msg_id}


def _mdict(m):
    return {"id": m.id, "room": m.room, "sender": m.sender, "text": m.text, "ts": m.ts.isoformat()}


# ---------------------------------------------------------------- stats
@app.get("/stats")
async def get_stats():
    con = _con()
    me = db.get_setting(con, "me")
    if not me:
        raise HTTPException(400, "me not set")
    msgs = db.all_messages(con)
    return {
        "me": me,
        "overview": stats.overview(msgs, me),
        "heatmap": stats.activity_heatmap(msgs, me),
        "by_hour": stats.activity_by_hour(msgs, me),
        "reply": stats.reply_stats(msgs, me)[:10],
        "reply_trend": stats.reply_trend(msgs, me),
        "style": stats.my_style(msgs, me),
        "unanswered": stats.unanswered(msgs, me, now=db.now_ts(con))[:10],
        "weekly": stats.weekly_report(msgs, me),
    }


# ---------------------------------------------------------------- chat
class ChatBody(BaseModel):
    messages: list[dict]  # [{"role": "user"|"assistant", "content": str}]


@app.post("/chat")
async def chat(body: ChatBody):
    coach = _coach()

    async def gen():
        buf = []
        try:
            async for t in coach.chat(body.messages):
                buf.append(t)
                yield f"data: {json.dumps({'delta': t}, ensure_ascii=False)}\n\n"
        except Exception as e:  # noqa: BLE001 — 키 없음/네트워크 등을 프론트에 그대로 알림
            msg = str(e)
            if "authentication" in msg.lower() or "api_key" in msg.lower() or "401" in msg:
                msg = "API 키가 없거나 잘못됐어. 프로젝트 폴더의 .env에 ANTHROPIC_API_KEY=... 를 넣고 백엔드를 재시작해줘."
            yield f"data: {json.dumps({'error': msg}, ensure_ascii=False)}\n\n"
            return
        full = "".join(buf)
        hl = None
        if m := _HL.search(full):
            try:
                hl = json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        yield f"data: {json.dumps({'done': True, 'highlight': hl, 'text': _HL.sub('', full).strip()}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/first_insight")
async def first_insight():
    text = await _coach().first_insight()
    hl = None
    if m := _HL.search(text):
        try:
            hl = json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return {"text": _HL.sub("", text).strip(), "highlight": hl}


class DraftBody(BaseModel):
    person: str


@app.post("/draft_reply")
async def draft_reply(body: DraftBody):
    raise HTTPException(501, "답장 초안: 말투 재현 규격 구현 중")


# ---------------------------------------------------------------- funeral (X 소환술 / 진단서 / 부적)
def _funeral() -> Funeral:
    con = _con()
    me, target = db.get_setting(con, "me"), db.get_setting(con, "target")
    if not me or not target:
        raise HTTPException(400, "먼저 나와 상대를 설정해줘")
    return Funeral(db.all_messages(con), me, target, db.now_ts(con), _persona_of(con, target))


@app.post("/summon")
async def summon(body: ChatBody):
    return await _funeral().summon(body.messages)


@app.get("/eulogy")
async def eulogy():
    return await _funeral().eulogy()


@app.get("/curse")
async def curse():
    return await _funeral().curse()


@app.get("/last_message")
async def last_message():
    con = _con()
    me, target = db.get_setting(con, "me"), db.get_setting(con, "target")
    if not me or not target:
        raise HTTPException(400, "me/target not set")
    from core.sessions import relationship_messages
    rel = relationship_messages(db.all_messages(con), me, target)
    return {"message": _mdict(rel[-1]) if rel else None}


# ---------------------------------------------------------------- connector (카톡 PC 자동 export) — PoC 확정 후 연결
@app.post("/connect/kakao")
async def connect_kakao():
    raise HTTPException(501, "kakao_win connector: PoC 진행 중")
