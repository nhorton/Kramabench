#!/usr/bin/env python3
"""Display a Claude Code session JSONL file in a readable, colorized form.

Usage:
    python scripts/show_transcript.py <path-to-session.jsonl>

Colors:
    blue   = user messages
    red    = assistant messages
    black  = tool calls / tool results (default terminal color)
"""

import argparse
import json
import sys
from pathlib import Path

BLUE = "\033[34m"
RED = "\033[31m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def stringify_content(content):
    """Return (text_blocks, tool_blocks) extracted from a message content field."""
    text_blocks = []
    tool_blocks = []
    if isinstance(content, str):
        text_blocks.append(content)
        return text_blocks, tool_blocks
    if not isinstance(content, list):
        return text_blocks, tool_blocks
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "text":
            text_blocks.append(block.get("text", ""))
        elif btype == "thinking":
            text_blocks.append(f"[thinking] {block.get('thinking', '')}")
        elif btype == "tool_use":
            name = block.get("name", "?")
            inp = block.get("input", {})
            try:
                inp_str = json.dumps(inp, indent=2, ensure_ascii=False)
            except (TypeError, ValueError):
                inp_str = str(inp)
            tool_blocks.append(f"→ tool_use: {name}\n{inp_str}")
        elif btype == "tool_result":
            inner = block.get("content", "")
            if isinstance(inner, list):
                parts = []
                for c in inner:
                    if isinstance(c, dict) and c.get("type") == "text":
                        parts.append(c.get("text", ""))
                    else:
                        parts.append(str(c))
                inner = "\n".join(parts)
            is_err = block.get("is_error")
            label = "tool_result (error)" if is_err else "tool_result"
            tool_blocks.append(f"← {label}\n{inner}")
        else:
            tool_blocks.append(f"[{btype}] {json.dumps(block, ensure_ascii=False)[:200]}")
    return text_blocks, tool_blocks


def render(path: Path, no_color: bool = False) -> None:
    blue = "" if no_color else BLUE
    red = "" if no_color else RED
    dim = "" if no_color else DIM
    bold = "" if no_color else BOLD
    reset = "" if no_color else RESET

    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            etype = entry.get("type")
            if etype not in ("user", "assistant"):
                continue

            msg = entry.get("message", {})
            role = msg.get("role") or etype
            content = msg.get("content")
            text_blocks, tool_blocks = stringify_content(content)

            color = blue if role == "user" else red
            label = "USER" if role == "user" else "ASSISTANT"

            for text in text_blocks:
                if not text.strip():
                    continue
                print(f"{color}{bold}{label}:{reset}{color} {text}{reset}")
                print()

            for tool in tool_blocks:
                print(f"{dim}{tool}{reset}")
                print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path, help="Path to a Claude Code session .jsonl file")
    ap.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    args = ap.parse_args()

    if not args.path.exists():
        print(f"File not found: {args.path}", file=sys.stderr)
        return 1
    render(args.path, no_color=args.no_color)
    return 0


if __name__ == "__main__":
    sys.exit(main())
