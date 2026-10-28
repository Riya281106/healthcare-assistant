"""Turns model output into plain, readable text (no raw Markdown symbols)."""

import re

_BOLD = re.compile(r"(\*\*|__)(.+?)\1", re.S)
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*", re.M)
_BULLET = re.compile(r"^\s*[\*\-]\s+", re.M)
_CODE_FENCE = re.compile(r"```[a-zA-Z]*\n?|```")
_INLINE_CODE = re.compile(r"`([^`]+)`")
_MANY_BLANKS = re.compile(r"\n{3,}")


def plain_text(text: str) -> str:
    if not isinstance(text, str):
        return text
    out = _CODE_FENCE.sub("", text)
    out = _BOLD.sub(r"\2", out)
    out = _INLINE_CODE.sub(r"\1", out)
    out = _HEADING.sub("", out)
    out = _BULLET.sub("• ", out)
    out = out.replace("**", "")
    out = _MANY_BLANKS.sub("\n\n", out)
    return out.strip()
