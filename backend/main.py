"""FastAPI 서버: 업로드/연결 → 통계 → 채팅(SSE) → 답장 초안."""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from contextvars import ContextVar

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

import db
import relationship
import cemetery
from fastapi import Header
from core.causes import diagnose as diagnose_causes
from core.signals import retro as retro_signals
from core.sessions import relationship_messages as _rel_msgs
import stats
from coach import Coach
from funeral import Funeral, legends_for
from parser import parse_file_meta

app = FastAPI(title="kakao-coach")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

UPLOAD_DIR = db.DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
_HL = re.compile(r"<highlight>(.*?)</highlight>", re.S)

# ---------------------------------------------------------------- 세션 격리
# 브라우저마다 X-Session(프론트의 익명 ID)을 보내고, 그 값으로 SQLite 파일을 나눈다.
# 나/상대/persona/메시지가 전부 그 파일 안이라 라우트는 손댈 게 없다. 헤더가 없으면(스크립트·구버전) 기본 파일.
_SID: ContextVar[str | None] = ContextVar("sid", default=None)
_SID_RE = re.compile(r"^[A-Za-z0-9_-]{6,64}$")


@app.middleware("http")
async def session_middleware(request: Request, call_next):
    sid = request.headers.get("x-session") or request.headers.get("x-anon")
    token = _SID.set(sid if sid and _SID_RE.match(sid) else None)
    try:
        return await call_next(request)
    finally:
        _SID.reset(token)


def _sid() -> str | None:
    return _SID.get()


# LLM을 부르는 라우트는 세션당·전체 호출 수를 제한한다 (키 잔액 보호). 메모리 슬라이딩 윈도우, 재시작하면 리셋.
from collections import deque as _deque
from time import time as _now
_LLM_PATHS = ("/chat", "/summon", "/eulogy", "/curse", "/legends", "/epitaph", "/first_insight")
_LIMITS = {"session_min": 12, "session_hour": 120, "global_hour": 900}
_hits: dict[str, _deque] = {}


def _rate_ok(key: str, limit: int, window_s: float) -> bool:
    q = _hits.setdefault(key, _deque())
    t = _now()
    while q and q[0] < t - window_s:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(t)
    return True


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if any(path.startswith(p) for p in _LLM_PATHS) and request.method != "OPTIONS":
        who = request.headers.get("x-session") or (request.client.host if request.client else "anon")
        if not (_rate_ok(f"s:{who}:m", _LIMITS["session_min"], 60) and _rate_ok(f"s:{who}:h", _LIMITS["session_hour"], 3600)):
            return JSONResponse({"detail": "너무 빨라. 1분만 쉬었다 다시 눌러줘"}, status_code=429)
        if not _rate_ok("g:h", _LIMITS["global_hour"], 3600):
            return JSONResponse({"detail": "지금 사람이 몰려서 AI가 잠깐 쉬는 중이야. 조금 있다 다시"}, status_code=429)
    return await call_next(request)


def _con():
    sid = _sid()
    return db.connect(db.DATA_DIR / "sessions" / f"{sid}.db") if sid else db.connect()


def _shared_con():
    """공동묘지 폴백처럼 모두가 같이 보는 데이터는 세션과 무관하게 한 파일."""
    return db.connect()


def _upload_dir() -> Path:
    d = UPLOAD_DIR / _sid() if _sid() else UPLOAD_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _coach() -> Coach:
    con = _con()
    me, target = db.get_setting(con, "me"), db.get_setting(con, "target")
    if not me or not target:
        raise HTTPException(400, "먼저 /me, /target 으로 나와 상대를 설정해줘")

    def on_update(patch: dict) -> dict:
        """코치의 update_context 툴 → persona 저장. note는 기존 context 뒤에 누적, 나머지는 덮어씀."""
        c2 = _con()
        cur = json.loads(db.get_setting(c2, "persona", "{}") or "{}")
        p = cur.get(target) or {}
        note = patch.pop("note", None)
        if note:
            prev = (p.get("context") or "").strip()
            p["context"] = (prev + ("\n" if prev else "") + note.strip())[-1500:]
        p.update(patch)
        cur[target] = p
        db.set_setting(c2, "persona", json.dumps(cur, ensure_ascii=False))
        return _persona_of(c2, target)

    return Coach(db.all_messages(con), me, target, db.now_ts(con), _persona_of(con, target), on_update=on_update)


@app.get("/")
@app.get("/health")
async def health():
    return {"ok": True, "service": "breakup-funeral-api"}


@app.get("/llm_check")
async def llm_check():
    """배포 진단: 키/워크스페이스 존재 여부와 실제 1회 호출 결과 (키 값은 노출 안 함)."""
    import os
    key = os.getenv("ANTHROPIC_API_KEY", ""); ws = os.getenv("ANTHROPIC_WORKSPACE_ID", "")
    out = {"key_set": bool(key), "key_prefix": key[:10] if key else None, "key_len": len(key), "workspace_set": bool(ws),
           "workspace_prefix": ws[:7] if ws else None, "model": os.getenv("CLAUDE_MODEL", "claude-opus-5")}
    try:
        from funeral import client, MODEL
        r = await client.messages.create(model=MODEL, max_tokens=1500, output_config={"effort": "low"},
                                         messages=[{"role": "user", "content": "say ok"}])
        out["call"] = "ok"; out["reply"] = "".join(b.text for b in r.content if b.type == "text")[:40]
    except Exception as e:  # noqa: BLE001
        out["call"] = "error"; out["error"] = f"{type(e).__name__}: {str(e)[:300]}"
    return out


# ---------------------------------------------------------------- ingest
@app.post("/upload")
async def upload(files: list[UploadFile] = File(...)):
    con = _con()
    added, rooms = 0, []
    for f in files:
        dest = _upload_dir() / Path(f.filename or 'upload.txt').name
        dest.write_bytes(await f.read())
        msgs, saved = parse_file_meta(dest)
        db.bump_saved_at(con, saved)
        added += db.insert_messages(con, msgs)
        rooms.append({"file": f.filename, "messages": len(msgs), "room": msgs[0].room if msgs else None,
                      "saved_at": saved.isoformat()})
    return {"added": added, "files": rooms, "senders": db.senders(con)[:20]}


class SampleBody(BaseModel):
    me: str | None = None        # 샘플 속 '나'(고연오)를 이 이름으로
    target: str | None = None    # 샘플 속 상대(김하늘)를 이 이름으로


SAMPLE_ME, SAMPLE_TARGET = "고연오", "김하늘"


def _rename(text: str, me: str | None, target: str | None) -> str:
    if me:
        text = text.replace(SAMPLE_ME, me).replace("연오야", f"{me[-2:]}야").replace("연오", me[-2:])
    if target:
        text = text.replace(SAMPLE_TARGET, target)
    return text


@app.post("/load_sample")
async def load_sample(body: SampleBody | None = None):
    """데모 데이터 적재. 이름을 주면 샘플의 '나'/'상대' 이름을 그걸로 바꿔서 넣는다 (자기 이름으로 보이게)."""
    me = (body.me or "").strip()[:20] if body else ""
    target = (body.target or "").strip()[:20] if body else ""
    if me and target and me == target:
        raise HTTPException(400, "내 이름과 상대 이름이 같아요")
    con = _con()
    db.clear(con)
    con.execute("DELETE FROM settings")
    con.commit()
    sample = Path(__file__).parent.parent / "sample"
    total = 0
    for p in sorted(sample.glob("*.txt")):
        msgs, saved = parse_file_meta(p)
        for m in msgs:
            m.sender = _rename(m.sender, me, target)
            m.room = _rename(m.room, me, target)
            m.text = _rename(m.text, me, target)
        db.bump_saved_at(con, saved)
        total += db.insert_messages(con, msgs)
    db.set_setting(con, "me", me or SAMPLE_ME)
    return {"added": total, "senders": db.senders(con)[:20], "me": me or SAMPLE_ME, "target": target or SAMPLE_TARGET}


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
    con = _con()
    if body.target == db.get_setting(con, "me"):
        raise HTTPException(400, "상대가 나 자신이에요. '누가 당신인가요'와 '누구를 보낼까요'를 다시 골라주세요.")
    db.set_setting(con, "target", body.target)
    return {"ok": True}


@app.get("/targets")
async def targets():
    con = _con()
    me = db.get_setting(con, "me")
    if not me:
        raise HTTPException(400, "me not set")
    return {"me": me, "target": db.get_setting(con, "target"), "candidates": relationship.candidates(db.all_messages(con), me)[:20]}


ENDED = {"ghosted", "dumped", "dumper", "faded", "mutual"}   # 사용자가 "끝났다"고 알려준 상태
ENDING_LABEL = {"ghosted": "잠수·읽씹", "dumped": "차였음", "dumper": "내가 끝냄", "faded": "자연소멸", "mutual": "합의 이별",
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
    if person == me:
        raise HTTPException(400, "상대가 나 자신이에요. 다른 사람을 골라주세요.")
    all_msgs = db.all_messages(con)
    rel_check = _rel_msgs(all_msgs, me, person)
    if sum(1 for x in rel_check if x.sender == me) < 5:
        raise HTTPException(400, f"{person}와(과) 주고받은 1:1 대화가 거의 없어요 (단톡에서만 등장). 1:1 대화방 txt를 올리거나 다른 사람을 골라주세요.")
    p = _persona_of(con, person)
    r = relationship.build(all_msgs, me, person, db.now_ts(con), started_at=relationship.parse_date(p.get("started_at")))
    ending = p.get("ending")
    # 사용자가 알려준 이별 컨텍스트가 데이터 판정을 덮어쓴다 (회피형 X = 데이터상 '썸'으로 보이는 경우 등)
    # 향년 시작점: 사용자가 찍은 시작일 > 데이터의 첫 썸/연애 구간 시작 > 첫 메시지
    first_warm = next((sg["start"] for sg in r["stages"]["segments"] if sg["stage"] in ("some", "dating")), None)
    r["user_context"] = {"ending": ending, "ending_label": ENDING_LABEL.get(ending), "context": p.get("context"),
                         "ended_at": p.get("ended_at"), "started_at": p.get("started_at"), "suggested_start": first_warm,
                         "overrides_stage": ending in ENDED}
    r["causes"] = diagnose_causes(rel_check, me, person, db.now_ts(con), r["user_context"])
    if ending in ENDED:
        r["stages"]["data_lens"] = r["stages"]["lens"]
        r["stages"]["data_label"] = r["stages"]["current_label"]
        r["stages"]["lens"] = "breakup"
        r["stages"]["current_stage"] = "ended"
        r["stages"]["current_label"] = f"이별 ({ENDING_LABEL[ending]})"
    r["signals"] = retro_signals(r["signals"], r["stages"]["lens"])
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
                if isinstance(t, dict):   # 툴 이벤트 (예: context_updated → 프론트가 진단서를 다시 받는다)
                    yield f"data: {json.dumps({'event': t}, ensure_ascii=False)}\n\n"
                    continue
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


@app.get("/epitaph")
async def epitaph(refresh: bool = False):
    """공동묘지 묘비 제목(어그로 한 줄). 사용자 진술(persona)이 바뀌면 다시 만든다."""
    import hashlib
    con = _con()
    me, target = db.get_setting(con, "me"), db.get_setting(con, "target")
    if not me or not target:
        raise HTTPException(400, "먼저 나와 상대를 설정해줘")
    p = _persona_of(con, target)
    ctx = {k: p.get(k) for k in ("ending", "context", "started_at", "ended_at")}
    key = f"epitaph:{target}:{hashlib.md5(json.dumps(ctx, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:10]}"
    if not refresh and (cached := db.get_setting(con, key)):
        return json.loads(cached)
    all_msgs = db.all_messages(con)
    rel = _rel_msgs(all_msgs, me, target)
    r = relationship.build(all_msgs, me, target, db.now_ts(con), started_at=relationship.parse_date(p.get("started_at")))
    first_warm = next((sg["start"] for sg in r["stages"]["segments"] if sg["stage"] in ("some", "dating")), None)
    uc = {"ending": p.get("ending"), "context": p.get("context"), "ended_at": p.get("ended_at"), "started_at": p.get("started_at")}
    causes = diagnose_causes(rel, me, target, db.now_ts(con), uc).get("causes") or []
    from datetime import datetime as _dt
    start = p.get("started_at") or first_warm or r["range"][0][:10]
    end = p.get("ended_at") or r["range"][1][:10]
    try:
        days = max(1, (_dt.fromisoformat(end) - _dt.fromisoformat(start)).days)
    except ValueError:
        days = None
    out = await _funeral().epitaph(causes, days)
    if out.get("epitaph"):
        db.set_setting(con, key, json.dumps(out, ensure_ascii=False))
    return out


@app.get("/eulogy")
async def eulogy():
    return await _funeral().eulogy()


@app.get("/curse")
async def curse():
    return await _funeral().curse()


@app.get("/legends")
async def legends(refresh: bool = False):
    """레전드 썰 매칭: 웹 검색 결과를 상대별로 캐시."""
    con = _con()
    target = db.get_setting(con, "target") or ""
    key = f"legends:{target}"
    if not refresh:
        cached = db.get_setting(con, key)
        if cached:
            return {**json.loads(cached), "cached": True}
    fun = _funeral()
    fun.brief["causes"] = None
    out = await legends_for(fun)
    if out.get("stories"):
        db.set_setting(con, key, json.dumps(out, ensure_ascii=False))
    return out


# ---------------------------------------------------------------- 공동묘지 (익명, 로그인 없음)
class BuryBody(BaseModel):
    epitaph: str
    kind: str = "chrys"
    days: int | None = None
    hanja: str | None = None


class CommentBody(BaseModel):
    text: str


def _anon(x_anon: str | None) -> str:
    if not x_anon or len(x_anon) < 6 or len(x_anon) > 64:
        raise HTTPException(400, "X-Anon 헤더(브라우저 익명 ID)가 필요해요")
    return x_anon


@app.get("/cemetery")
async def cemetery_list(x_anon: str | None = Header(default=None)):
    return cemetery.list_tombs(_shared_con(), x_anon)


@app.post("/cemetery")
async def cemetery_bury(body: BuryBody, x_anon: str | None = Header(default=None)):
    return cemetery.bury(_shared_con(), _anon(x_anon), body.epitaph, body.kind, body.days, body.hanja)


@app.post("/cemetery/{tomb_id}/flower")
async def cemetery_flower(tomb_id: int, x_anon: str | None = Header(default=None)):
    return cemetery.flower(_shared_con(), tomb_id, _anon(x_anon))


@app.get("/cemetery/{tomb_id}/comments")
async def cemetery_comments(tomb_id: int):
    return {"comments": cemetery.comments(_shared_con(), tomb_id)}


@app.post("/cemetery/{tomb_id}/comments")
async def cemetery_comment(tomb_id: int, body: CommentBody, x_anon: str | None = Header(default=None)):
    try:
        return cemetery.add_comment(_shared_con(), tomb_id, _anon(x_anon), body.text)
    except ValueError:
        raise HTTPException(400, "내용이 비었어요")


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
