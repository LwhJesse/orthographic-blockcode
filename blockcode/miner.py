from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, List

WORD_RE = re.compile(r"[A-Za-z]+")


def iter_words(text: str):
    for m in WORD_RE.finditer(text):
        w = m.group(0).lower()
        if w.isascii() and w.isalpha():
            yield w


def mine_chunks_from_text(text: str, min_len: int = 2, max_len: int = 8, top: int = 500) -> List[dict]:
    counts = Counter()
    prefix_counts = Counter()
    suffix_counts = Counter()
    word_counts = Counter(iter_words(text))

    for word, wf in word_counts.items():
        n = len(word)
        for L in range(min_len, min(max_len, n) + 1):
            for i in range(0, n - L + 1):
                chunk = word[i:i+L]
                counts[chunk] += wf
                if i == 0:
                    prefix_counts[chunk] += wf
                if i + L == n:
                    suffix_counts[chunk] += wf

    rows = []
    for chunk, freq in counts.items():
        saved_per_hit = max(len(chunk) - 1, 0)
        rows.append({
            "chunk": chunk,
            "length": len(chunk),
            "freq": freq,
            "prefix_freq": prefix_counts.get(chunk, 0),
            "suffix_freq": suffix_counts.get(chunk, 0),
            "score": freq * saved_per_hit,
            "suggested_scope": (
                "suffix" if suffix_counts.get(chunk, 0) >= max(prefix_counts.get(chunk, 0), freq * 0.5)
                else "prefix" if prefix_counts.get(chunk, 0) >= freq * 0.5
                else "any"
            ),
        })
    rows.sort(key=lambda r: (-r["score"], -r["freq"], -r["length"], r["chunk"]))
    return rows[:top]


def write_chunks(path: str | Path, rows: List[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
