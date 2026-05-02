from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator

WORD_RE = re.compile(r"[A-Za-z]+")
TOKEN_RE = re.compile(r"[A-Za-z]+|.", re.DOTALL)


@dataclass(frozen=True)
class Token:
    kind: str  # "word" or "literal"
    text: str
    index: int


def tokenize(text: str) -> Iterator[Token]:
    for idx, m in enumerate(TOKEN_RE.finditer(text)):
        tok = m.group(0)
        yield Token(kind="word" if WORD_RE.fullmatch(tok) else "literal", text=tok, index=idx)
