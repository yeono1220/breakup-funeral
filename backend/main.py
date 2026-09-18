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
    persona = json.loads(db.get_setting(con, "persona", "{}") or "{}").get(target) or {}
    return Coach(db.all_messages(con), me, target, db.now_ts(con), persona)


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


class PersonaBody(BaseModel):
    person: str
    mbti: str | None = None          # "ENFP" | None(모름)
    attachment: str | None = None    # secure | anxious | avoidant | fearful | None
    note: str | None = None          # 자유 메모 ("취미: 러닝")


@app.post("/persona")
async def set_persona(body: PersonaBody):
    con = _con()
    cur = json.loads(db.get_setting(con, "persona", "{}") or "{}")
    cur[body.person] = {k: v for k, v in body.model_dump().items() if k != "person"}
    db.set_setting(con, "persona", json.dumps(cur, ensure_ascii=False))
    return {"ok": True, "persona": cur[body.person]}


@app.get("/persona/{person}")
async def get_persona(person: str):
    cur = json.loads(db.get_setting(_con(), "persona", "{}") or "{}")
    return {"person": person, **(cur.get(person) or {"mbti": None, "attachment": None, "note": None})}


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
    return relationship.build(db.all_messages(con), me, person, db.now_ts(con))


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
    persona = json.loads(db.get_setting(con, "persona", "{}") or "{}").get(target) or {}
    return Funeral(db.all_messages(con), me, target, db.now_ts(con), persona)


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
