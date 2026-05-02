from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

from .model import PathInfo, Rule, Settings


class Encoder:
    """Enumerates distinct codes for a word under a fixed ruleset.

    Important dedup invariant:
      For one word, multiple segmentation paths may produce the same code.
      We keep only one canonical PathInfo per code.

    This prevents candidate lists and cost estimates from being polluted by
    segmentation artifacts.
    """

    def __init__(self, rules: List[Rule], settings: Settings):
        self.rules = list(rules)
        self.settings = settings
        self._cache: Dict[str, Dict[str, PathInfo]] = {}

        # Index by first char to avoid scanning all rules at every position.
        self.rules_by_first: Dict[str, List[Rule]] = defaultdict(list)
        for r in self.rules:
            if r.chunk:
                self.rules_by_first[r.chunk[0]].append(r)
        for ch in self.rules_by_first:
            self.rules_by_first[ch].sort(key=lambda r: (-len(r.chunk), r.chunk, r.code, r.rule_id))

    def _tie_better(self, new: PathInfo, old: PathInfo) -> bool:
        # Prefer fewer segments (larger chunks), then stable lexical order.
        if len(new.segments) != len(old.segments):
            return len(new.segments) < len(old.segments)
        if new.segments != old.segments:
            return new.segments < old.segments
        return new.rule_ids < old.rule_ids

    def enumerate_codes(self, word: str) -> Dict[str, PathInfo]:
        word = word.lower()
        if word in self._cache:
            return self._cache[word]
        if not word.isascii() or not word.isalpha():
            return {}
        if len(word) > self.settings.max_encoded_word_len:
            return {}

        n = len(word)
        dp: List[Dict[str, PathInfo]] = [dict() for _ in range(n + 1)]
        dp[0][""] = PathInfo(code="", segments=(), rule_ids=())

        for i in range(n):
            if not dp[i]:
                continue

            matches = []
            for r in self.rules_by_first.get(word[i], []):
                if r.matches(word, i):
                    matches.append(r)

            if self.settings.literal_letter_fallback:
                # Literal fallback as synthetic rule.
                matches.append(Rule(
                    rule_id="literal",
                    chunk=word[i],
                    code=word[i],
                    enabled=True,
                ))

            for prefix_code, path in list(dp[i].items()):
                for r in matches:
                    j = i + len(r.chunk)
                    if j > n:
                        continue
                    new_code = prefix_code + r.code
                    new_path = PathInfo(
                        code=new_code,
                        segments=path.segments + (r.chunk,),
                        rule_ids=path.rule_ids + (r.rule_id,),
                    )
                    old = dp[j].get(new_code)
                    if old is None or self._tie_better(new_path, old):
                        dp[j][new_code] = new_path

        self._cache[word] = dp[n]
        return dp[n]
