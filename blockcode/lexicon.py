from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Dict, Optional

WORD_RE = re.compile(r"[A-Za-z]+")


def load_lexicon(path: Optional[str | Path], fallback_text: Optional[str] = None) -> Dict[str, int]:
    """Load word frequencies.

    Accepted formats:
      word<TAB>freq
      word, freq
      word freq
      word

    If path is None, build a tiny article-derived lexicon from fallback_text.
    """
    freq: Counter[str] = Counter()

    if path is None:
        if fallback_text is None:
            raise ValueError("fallback_text required if lexicon path is None")
        for m in WORD_RE.finditer(fallback_text):
            w = m.group(0).lower()
            if w.isascii() and w.isalpha():
                freq[w] += 1
        return dict(freq)

    path = Path(path)
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # split by TSV, CSV-ish comma, or whitespace
            if "\t" in line:
                parts = line.split("\t")
            elif "," in line:
                parts = [p.strip() for p in line.split(",")]
            else:
                parts = re.split(r"\s+", line)
            word = parts[0].lower()
            if not word.isascii() or not word.isalpha():
                continue
            val = 1
            if len(parts) >= 2 and parts[1]:
                try:
                    val = int(float(parts[1]))
                except ValueError:
                    val = 1
            freq[word] += max(val, 1)
    return dict(freq)
