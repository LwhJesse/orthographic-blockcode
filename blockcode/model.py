from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class Scope(str, Enum):
    ANY = "any"
    PREFIX = "prefix"
    SUFFIX = "suffix"
    WHOLE = "whole"


@dataclass(frozen=True)
class Rule:
    rule_id: str
    chunk: str
    code: str
    scope: Scope = Scope.ANY
    cls: str = ""
    enabled: bool = True
    group: str = ""
    note: str = ""

    def matches(self, word: str, i: int) -> bool:
        if not self.enabled:
            return False
        if not word.startswith(self.chunk, i):
            return False
        j = i + len(self.chunk)
        n = len(word)
        if self.scope == Scope.ANY:
            return True
        if self.scope == Scope.PREFIX:
            return i == 0
        if self.scope == Scope.SUFFIX:
            return j == n
        if self.scope == Scope.WHOLE:
            return i == 0 and j == n
        return False


@dataclass(frozen=True)
class CommitModel:
    rank1_key: str = ";"
    rank2_key: str = "'"
    bare_commit_cost: int = 1
    eof_rank0_commit_cost: int = 0
    punctuation_committers: Tuple[str, ...] = (",", ".", "?", "!", ":", ";")
    auto_consume_space_after_punctuation: bool = True
    rank_selection_consumes_space_boundary: bool = True


@dataclass(frozen=True)
class Settings:
    literal_letter_fallback: bool = True
    raw_prefix_cost: int = 1
    max_encoded_word_len: int = 48
    uppercase_extra_cost: int = 1
    unknown_char_cost: int = 1
    # kept for backward compatibility / non-delimiter model; v0.4 uses max_candidate_rank + commit model
    selection_costs: Tuple[int, ...] = (0, 1, 2, 2, 3, 3, 4, 4, 5, 5)
    unlisted_rank_cost: int = 99
    candidate_preview: int = 10
    max_candidate_rank: int = 3
    commit_model: CommitModel = CommitModel()

    def rank_cost(self, rank_zero_based: int) -> int:
        if 0 <= rank_zero_based < len(self.selection_costs):
            return self.selection_costs[rank_zero_based]
        return self.unlisted_rank_cost


@dataclass(frozen=True)
class PathInfo:
    code: str
    segments: Tuple[str, ...]
    rule_ids: Tuple[str, ...]


@dataclass(frozen=True)
class DelimiterInfo:
    kind: str          # space, punct, eof, other
    literal: str       # visible delimiter char, if any
    consumed_len: int  # chars consumed by commit action after the word
    auto_consumed_space: bool = False


@dataclass(frozen=True)
class WordResult:
    token: str
    normalized: str
    mode: str
    cost: int
    baseline_cost: int
    fallback_cost: int
    saved: int
    code: str = ""
    input_sequence: str = ""
    rank: Optional[int] = None
    candidate_count: int = 0
    segments: Tuple[str, ...] = ()
    rule_ids: Tuple[str, ...] = ()
    candidates_preview: Tuple[str, ...] = ()
    case_extra_cost: int = 0
    consumed_next_chars: int = 0
    delimiter_kind: str = ""
    delimiter_literal: str = ""
    auto_consumed_space: bool = False
