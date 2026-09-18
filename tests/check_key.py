"""API 키/모델 연결 점검.  python tests/check_key.py"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
k = os.getenv("ANTHROPIC_API_KEY", "")
print("key loaded:", (k[:14] + "...") if k else None, "len", len(k))
if not k:
    sys.exit("no key")
import anthropic  # noqa: E402

ws = os.getenv("ANTHROPIC_WORKSPACE_ID")
print("workspace:", ws or "(none)")
c = anthropic.Anthropic(default_headers={"anthropic-workspace-id": ws} if ws else None)
model = os.getenv("CLAUDE_MODEL", "claude-opus-5")
try:
    r = c.messages.create(model=model, max_tokens=2000, output_config={"effort": "low"}, messages=[{"role": "user", "content": "hi"}])
    print("OK", model, "->", "".join(b.text for b in r.content if b.type == "text"))
except Exception as e:  # noqa: BLE001
    print("ERR", type(e).__name__, str(e)[:400])
