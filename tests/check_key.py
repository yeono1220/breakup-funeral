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
    r = c.messages.create(model=model, max_tokens=20, messages=[{"role": "user", "content": "hi"}])
    print("OK", model, "->", r.content[0].text)
except Exception as e:  # noqa: BLE001
    print("ERR", type(e).__name__, str(e)[:400])
