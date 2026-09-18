"""프롬프트 눈검사 하네스.  PYTHONIOENCODING=utf-8 python tests/prompt_eval.py [--me 이름] [--target 이름] [--only summon,eulogy,curse] [--tag before]

로컬 DB(backend/data/coach.db)의 실데이터로 소환술·진단서·부적을 고정 입력으로 돌려
결과 + 코드 검증 결과를 backend/data/evals/<tag>_<시각>.md 에 저장한다 (gitignore 안).
원문 카톡은 출력하지 않고 LLM 산출물만 남긴다.
"""
import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import db  # noqa: E402
from funeral import Funeral  # noqa: E402

SUMMON_INPUTS = [
    "보고 싶어",
    "우리 다시 만날까?",
    "그때 왜 그랬어?",
    "잘 지내?",
    "나 아직도 네 생각 나",
    "내가 뭘 잘못했는지 말이라도 해줘",
    "밥은 먹었어",
    "너 지금 뭐해",
]


def persona_of(con, target: str) -> dict:
    cur = json.loads(db.get_setting(con, "persona", "{}") or "{}")
    p = dict(cur.get(target) or {})
    p.pop("portrait", None)
    return p


async def run(args):
    con = db.connect()
    me = args.me or db.get_setting(con, "me")
    target = args.target or db.get_setting(con, "target")
    fun = Funeral(db.all_messages(con), me, target, db.now_ts(con), persona_of(con, target))
    only = set(args.only.split(",")) if args.only else {"summon", "eulogy", "curse"}
    out = [f"# prompt eval — {args.tag} — {datetime.now():%Y-%m-%d %H:%M}", f"me={me} target={target} rel={len(fun.rel)}", ""]

    if "summon" in only:
        out.append("## summon")
        for q in SUMMON_INPUTS:
            t0 = time.time()
            r = await fun.summon([{"role": "user", "content": q}])
            dt = time.time() - t0
            bubbles = r.get("bubbles") or [r.get("reply", "")]
            flag = " (fallback)" if r.get("fallback") else ""
            check = r.get("check")
            out.append(f"- 나: {q}")
            for b in bubbles:
                out.append(f"  - {target}: {b}")
            out.append(f"  - _{dt:.1f}s{flag}{(' check=' + json.dumps(check, ensure_ascii=False)) if check else ''}_")
        out.append("")

    if "eulogy" in only:
        out.append("## eulogy")
        for i in range(args.n_eulogy):
            t0 = time.time()
            r = await fun.eulogy()
            out.append(f"### #{i + 1} ({time.time() - t0:.1f}s{' fallback' if r.get('fallback') else ''}{' check=' + json.dumps(r['check'], ensure_ascii=False) if r.get('check') else ''})")
            out.append(r["text"])
            out.append("")

    if "curse" in only:
        out.append("## curse")
        for i in range(args.n_curse):
            t0 = time.time()
            r = await fun.curse()
            out.append(f"- {r['line']}  _({time.time() - t0:.1f}s{' fallback' if r.get('fallback') else ''}{' cands=' + json.dumps(r['candidates'], ensure_ascii=False) if r.get('candidates') else ''})_")
        out.append("")

    text = "\n".join(out)
    print(text)
    d = ROOT / "backend" / "data" / "evals"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{args.tag}_{datetime.now():%m%d_%H%M}.md"
    f.write_text(text, encoding="utf-8")
    print(f"\nsaved → {f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--me")
    ap.add_argument("--target")
    ap.add_argument("--only")
    ap.add_argument("--tag", default="run")
    ap.add_argument("--n-eulogy", type=int, default=2)
    ap.add_argument("--n-curse", type=int, default=3)
    asyncio.run(run(ap.parse_args()))
