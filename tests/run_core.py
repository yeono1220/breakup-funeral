"""샘플 데이터로 core 지표 전부 실행해 눈으로 확인하는 스크립트.  python tests/run_core.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from parser import parse_file_meta  # noqa: E402
from core.sessions import relationship_messages, other_messages  # noqa: E402
from core.symmetry import symmetry, my_bias, waiting_reply  # noqa: E402
from core.temperature import baseline_q, temperature_now, weekly_series, updown_events  # noqa: E402
from core.stages import detect_stages  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def load(sample_dir=ROOT / "sample"):
    allm, saved = [], None
    for f in sorted(sample_dir.glob("*.txt")):
        m, s = parse_file_meta(f)
        allm += m
        saved = max(saved or s, s)
    for i, m in enumerate(allm):
        m.id = i + 1
    allm.sort(key=lambda m: m.ts)
    return allm, saved


def main(me="고연오", target="김하늘", friend="박민수"):
    allm, saved = load()
    rel = relationship_messages(allm, me, target)
    base = baseline_q(other_messages(allm, rel), me)
    print(f"rel={len(rel)} now={saved} base={base}")

    t = temperature_now(rel, me, target, base, now=saved)
    print(f"\n== now: {t['temp']}  Δweek {t['delta_week']}  sparse={t['sparse']} norm_pd={t['norm_per_day']} top={t['top_factor']}")
    for k, v in t["components"].items():
        print(f"   {k} {v['label']}: {v['value']} → {v['contrib']}")

    ws = weekly_series(rel, me, target, base)
    print("\n== weekly:", " ".join(f"{w['week_start'][5:]}={w['temp']}" for w in ws))
    print("\n== updown")
    for e in updown_events(ws, rel, target):
        arrow = "▲" if e["direction"] == "up" else "▼"
        print(f"   {e['week_start']} {arrow} {e['delta']:+} → {e['temp']} top={e['top_factor']['label'] if e['top_factor'] else None} ev={[p['text'] for p in e['evidence_preview']]}")

    st = detect_stages(ws)
    print(f"\n== stages: current={st['current_label']} lens={st['lens']}")
    for s in st["segments"]:
        print(f"   {s['label']:>3} {s['start']} ~ {s['end']} ({s['weeks']}w, conf {s['confidence']})")

    sym = symmetry(rel, me, target)
    print("\n== symmetry")
    for b in sym["bars"]:
        print(f"   {b['label']}: me={b['me']} them={b['them']} share={b['share']}")
    print("   reply:", sym["reply"])
    bias = my_bias(allm, rel, me, target)
    print(f"\n== bias: reply x{bias['reply_speed']['times_faster']} ({bias['reply_speed']['to_target_min']}m vs {bias['reply_speed']['to_others_min']}m), len x{bias['length']['times']}, kkk x{bias['kkk']['times']}, late {bias['late_night']}")
    print("== waiting:", waiting_reply(rel, me, target, saved))

    relF = relationship_messages(allm, me, friend)
    bf = my_bias(allm, relF, me, friend)
    print(f"\n== compare {friend}: my reply {symmetry(relF, me, friend)['reply']} | speed x{bf['reply_speed']['times_faster']}")


if __name__ == "__main__":
    main(*sys.argv[1:])
