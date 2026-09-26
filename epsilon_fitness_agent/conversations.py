"""Per-user conversation persistence.

Lets the agent recall earlier sessions across time (requirement 5: an ongoing
personal assistant), not just earlier turns within a single conversation.
"""

import json
from pathlib import Path

CONVERSATIONS_DIR = Path(__file__).resolve().parent.parent / "data" / "conversations"


def _serialize_content(content):
    """API messages may hold SDK content-block objects (pydantic models) -
    convert to plain JSON-safe dicts. Plain strings/dicts pass through."""
    if isinstance(content, str):
        return content
    blocks = []
    for block in content:
        blocks.append(block.model_dump(mode="json") if hasattr(block, "model_dump") else block)
    return blocks


def _reconstruct_display(messages: list[dict]) -> list[dict]:
    """Fallback UI-display reconstruction from raw API messages, used when a
    conversation was saved without a `display` list (e.g. from the CLI)."""
    display = []
    for m in messages:
        content = m["content"]
        if isinstance(content, str):
            if m["role"] == "user":
                display.append({"role": "user", "text": content})
            continue
        if m["role"] == "assistant":
            tools = [b["name"] for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
            text = next(
                (b["text"] for b in content if isinstance(b, dict) and b.get("type") == "text"), None
            )
            if text:
                display.append({"role": "assistant", "text": text, "tools": tools})
    return display


def load_conversation(user_id: str) -> dict:
    """Returns {"messages": [...], "display": [...]} - both empty if there's
    no saved conversation for this user yet."""
    path = CONVERSATIONS_DIR / f"{user_id}.json"
    if not path.exists():
        return {"messages": [], "display": []}

    with open(path) as f:
        saved = json.load(f)

    messages = saved.get("messages", [])
    display = saved.get("display") or _reconstruct_display(messages)
    return {"messages": messages, "display": display}


def save_conversation(user_id: str, messages: list[dict], display: list[dict] | None = None) -> None:
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "messages": [{"role": m["role"], "content": _serialize_content(m["content"])} for m in messages],
        "display": display or [],
    }
    path = CONVERSATIONS_DIR / f"{user_id}.json"
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)


def clear_conversation(user_id: str) -> None:
    path = CONVERSATIONS_DIR / f"{user_id}.json"
    path.unlink(missing_ok=True)
