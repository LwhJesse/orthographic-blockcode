from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .encoder import Encoder
from .model import Rule, Settings, WordResult, DelimiterInfo

WORD_AT = re.compile(r"[A-Za-z]+")
ASCII_WORD = re.compile(r"[A-Za-z]+")


class Evaluator:
    """Delimiter-aware evaluator.

    v0.4 key correction:
    A word's input is not merely `code + rank_cost`.
    It is `code + commit action`, and the commit action may consume the
    following delimiter/boundary.

    Examples under default settings:
      see + space   -> su<space>
      sea + space   -> su;
      see + comma+space -> su,
      sea + comma+space -> su;,
      sea + semicolon+space -> su;;
      third candidate + space -> code'
    """

    def __init__(self, rules: List[Rule], settings: Settings, lexicon_freq: Dict[str, int]):
        self.rules = rules
        self.settings = settings
        self.lexicon_freq = lexicon_freq
        self.encoder = Encoder(rules, settings)
        self.index: Dict[str, List[str]] = {}
        self._word_result_cache: Dict[tuple[str, str, str, int], WordResult] = {}
        self.build_candidate_index()

    def literal_cost(self, text: str) -> int:
        return sum(1 if ord(ch) < 128 else self.settings.unknown_char_cost for ch in text)

    def baseline_word_cost(self, token: str) -> int:
        return self.literal_cost(token) + self.case_extra(token)

    def fallback_word_cost(self, token: str) -> int:
        return self.settings.raw_prefix_cost + self.baseline_word_cost(token)

    def case_extra(self, token: str) -> int:
        return sum(1 for ch in token if "A" <= ch <= "Z") * self.settings.uppercase_extra_cost

    def raw_input_sequence(self, token: str) -> str:
        # Symbolic raw fallback sequence.
        # ⎋ means "enter literal/raw spelling mode" and costs raw_prefix_cost.
        # Uppercase letters are represented as ⇧x to make the key log reflect
        # the uppercase_extra_cost model.
        parts = ["⎋"]
        for ch in token:
            if "A" <= ch <= "Z":
                parts.append("⇧" + ch.lower())
            elif ch == "\n":
                parts.append("\\n")
            else:
                parts.append(ch)
        return "".join(parts)

    def apply_case_marker(self, token: str, seq: str) -> str:
        # Minimal symbolic casing model for encoded candidates.
        # If the visible token contains uppercase letters, prepend shift markers.
        # This is deliberately symbolic: a real IME may implement casing differently.
        uppers = [ch for ch in token if "A" <= ch <= "Z"]
        if not uppers:
            return seq
        return "".join("⇧" + ch.lower() for ch in uppers) + seq

    def build_candidate_index(self) -> None:
        tmp: Dict[str, set[str]] = defaultdict(set)
        for word in self.lexicon_freq:
            for code in self.encoder.enumerate_codes(word):
                tmp[code].add(word)
        self.index = {
            code: sorted(words, key=lambda w: (-self.lexicon_freq.get(w, 1), w))
            for code, words in tmp.items()
        }

    def delimiter_after(self, text: str, pos: int) -> DelimiterInfo:
        """Classify the target delimiter immediately after a word.

        consumed_len means chars that the commit action can produce/consume
        as part of the word input.

        Important default semantics:
        - space boundary can be consumed by rank0 Space, rank1 ;, rank2 '.
        - punctuation key commits rank0 and emits punctuation.
        - after punctuation, one target ASCII space can be auto-consumed.
        - for rank1/rank2 before punctuation, selection key commits word,
          then punctuation key emits punctuation and auto-space.
        """
        if pos >= len(text):
            return DelimiterInfo(kind="eof", literal="", consumed_len=0)

        ch = text[pos]
        if ch == " ":
            return DelimiterInfo(kind="space", literal=" ", consumed_len=1)

        if ch in self.settings.commit_model.punctuation_committers:
            consumed = 1
            auto_space = False
            if (
                self.settings.commit_model.auto_consume_space_after_punctuation
                and pos + 1 < len(text)
                and text[pos + 1] == " "
            ):
                consumed += 1
                auto_space = True
            return DelimiterInfo(kind="punct", literal=ch, consumed_len=consumed, auto_consumed_space=auto_space)

        if ch == "\n":
            # newline is not treated as rank-selection-consumable by default,
            # but rank0 can use Enter as a committing delimiter.
            return DelimiterInfo(kind="newline", literal="\n", consumed_len=1)

        return DelimiterInfo(kind="other", literal=ch, consumed_len=0)

    def commit_cost_and_sequence(self, code: str, rank: int, delim: DelimiterInfo) -> tuple[Optional[int], str, int]:
        """Return (extra_cost_after_code, visible-ish input sequence, consumed_next_chars).

        rank:
          0 = first candidate
          1 = second candidate via ;
          2 = third candidate via '

        Ranks >= max_candidate_rank are disallowed.
        """
        cm = self.settings.commit_model
        if rank >= self.settings.max_candidate_rank:
            return None, "", 0

        if rank == 0:
            if delim.kind == "eof":
                return cm.eof_rank0_commit_cost, code, 0
            if delim.kind == "space":
                return 1, code + "␠", delim.consumed_len
            if delim.kind == "punct":
                return 1, code + delim.literal, delim.consumed_len
            if delim.kind == "newline":
                return 1, code + "\\n", delim.consumed_len
            # Need a bare commit to finalize word before an attached literal.
            return cm.bare_commit_cost, code + "⏎", 0

        select_key = cm.rank1_key if rank == 1 else cm.rank2_key

        if delim.kind == "eof":
            return 1, code + select_key, 0

        if delim.kind == "space" and cm.rank_selection_consumes_space_boundary:
            # sea + space -> su; ; no actual space key.
            return 1, code + select_key, delim.consumed_len

        if delim.kind == "punct":
            # sea + comma(+space) -> su;, ; punctuation key emits punctuation and optional following space.
            return 2, code + select_key + delim.literal, delim.consumed_len

        if delim.kind == "newline":
            # selection commits word, then Enter emits newline.
            return 2, code + select_key + "\\n", delim.consumed_len

        # selection commits word; next literal will be processed normally.
        return 1, code + select_key, 0

    def best_word_result(self, token: str, delim: DelimiterInfo) -> WordResult:
        norm = token.lower()
        cache_key = (token, delim.kind, delim.literal, delim.consumed_len)
        if cache_key in self._word_result_cache:
            return self._word_result_cache[cache_key]

        baseline = self.baseline_word_cost(token)
        fallback = self.fallback_word_cost(token)
        case_extra = self.case_extra(token)

        # Raw fallback does not consume the following delimiter. It is exact literal spelling.
        raw_input = self.raw_input_sequence(token)
        raw_res = WordResult(
            token=token,
            normalized=norm,
            mode="raw",
            cost=fallback,
            baseline_cost=baseline,
            fallback_cost=fallback,
            saved=baseline - fallback,
            input_sequence=raw_input,
            case_extra_cost=case_extra,
            consumed_next_chars=0,
            delimiter_kind=delim.kind,
            delimiter_literal=delim.literal,
        )

        if (
            not norm.isascii()
            or not norm.isalpha()
            or len(norm) > self.settings.max_encoded_word_len
            or norm not in self.lexicon_freq
        ):
            self._word_result_cache[cache_key] = raw_res
            return raw_res

        best: Optional[WordResult] = None
        codes = self.encoder.enumerate_codes(norm)

        for code, path in codes.items():
            cands = self.index.get(code, [])
            try:
                rank = cands.index(norm)
            except ValueError:
                continue

            extra, seq, consumed = self.commit_cost_and_sequence(code, rank, delim)
            if extra is None:
                continue

            cost = len(code) + extra + case_extra
            res = WordResult(
                token=token,
                normalized=norm,
                mode="encoded",
                cost=cost,
                baseline_cost=baseline,
                fallback_cost=fallback,
                saved=baseline - cost,
                code=code,
                input_sequence=self.apply_case_marker(token, seq),
                rank=rank,
                candidate_count=len(cands),
                segments=path.segments,
                rule_ids=path.rule_ids,
                candidates_preview=tuple(cands[: self.settings.candidate_preview]),
                case_extra_cost=case_extra,
                consumed_next_chars=consumed,
                delimiter_kind=delim.kind,
                delimiter_literal=delim.literal,
                auto_consumed_space=delim.auto_consumed_space if consumed else False,
            )
            if best is None:
                best = res
            else:
                new_key = (res.cost, res.rank if res.rank is not None else 999999, len(res.code), len(res.segments), res.code)
                old_key = (best.cost, best.rank if best.rank is not None else 999999, len(best.code), len(best.segments), best.code)
                if new_key < old_key:
                    best = res

        # Raw fallback may be cheaper, but it does not consume delimiter.
        if best is None or raw_res.cost < best.cost:
            final = raw_res
        else:
            final = best
        self._word_result_cache[cache_key] = final
        return final

    def evaluate_text(self, text: str) -> Tuple[List[dict], dict]:
        rows: List[dict] = []
        total_cost = 0
        baseline_total = self.literal_cost(text) + sum(1 for ch in text if "A" <= ch <= "Z")
        encoded_words = 0
        raw_words = 0
        word_count = 0
        literal_count = 0
        non_ascii_count = 0
        consumed_literal_chars = 0

        i = 0
        idx = 0
        n = len(text)
        while i < n:
            m = WORD_AT.match(text, i)
            if m:
                token = m.group(0)
                word_count += 1
                delim = self.delimiter_after(text, m.end())
                res = self.best_word_result(token, delim)
                total_cost += res.cost
                if res.mode == "encoded":
                    encoded_words += 1
                else:
                    raw_words += 1

                rows.append({
                    "index": idx,
                    "type": "word",
                    "token": token,
                    "normalized": res.normalized,
                    "mode": res.mode,
                    "cost": res.cost,
                    "baseline_word_cost": res.baseline_cost,
                    "fallback_word_cost": res.fallback_cost,
                    "saved_vs_word_baseline": res.saved,
                    "code": res.code,
                    "input_sequence": res.input_sequence,
                    "rank": "" if res.rank is None else res.rank + 1,
                    "candidate_count": res.candidate_count,
                    "delimiter_kind": res.delimiter_kind,
                    "delimiter_literal": res.delimiter_literal.replace("\n", "\\n"),
                    "consumed_next_chars": res.consumed_next_chars,
                    "auto_consumed_space": int(res.auto_consumed_space),
                    "segments": " + ".join(res.segments),
                    "rules": " + ".join(res.rule_ids),
                    "candidates_preview": " ".join(res.candidates_preview),
                })
                # Advance over word and any delimiter chars consumed by commit action.
                i = m.end() + res.consumed_next_chars
                consumed_literal_chars += res.consumed_next_chars
                idx += 1
            else:
                ch = text[i]
                c = self.literal_cost(ch)
                total_cost += c
                literal_count += 1
                if ord(ch) >= 128:
                    non_ascii_count += 1
                rows.append({
                    "index": idx,
                    "type": "literal",
                    "token": ch.replace("\n", "\\n"),
                    "normalized": ch.replace("\n", "\\n"),
                    "mode": "literal",
                    "cost": c,
                    "baseline_word_cost": c,
                    "fallback_word_cost": c,
                    "saved_vs_word_baseline": 0,
                    "code": ch if ord(ch) < 128 else "",
                    "input_sequence": ch.replace("\n", "\\n"),
                    "rank": "",
                    "candidate_count": "",
                    "delimiter_kind": "",
                    "delimiter_literal": "",
                    "consumed_next_chars": "",
                    "auto_consumed_space": "",
                    "segments": "",
                    "rules": "",
                    "candidates_preview": "",
                })
                i += 1
                idx += 1

        summary = {
            "total_cost": total_cost,
            "baseline_total": baseline_total,
            "saved": baseline_total - total_cost,
            "reduction_ratio": (baseline_total - total_cost) / baseline_total if baseline_total else 0.0,
            "word_count": word_count,
            "encoded_word_count": encoded_words,
            "raw_word_count": raw_words,
            "literal_count_unconsumed": literal_count,
            "literal_chars_consumed_by_commit": consumed_literal_chars,
            "non_ascii_literal_count": non_ascii_count,
            "lexicon_size": len(self.lexicon_freq),
            "candidate_code_count": len(self.index),
            "model": "delimiter-aware-v0.4",
        }
        return rows, summary

    def analyze_lexicon(self) -> Tuple[List[dict], dict, List[dict]]:
        # Lexicon analysis uses EOF delimiter by default, because no article delimiter is known.
        eof = DelimiterInfo(kind="eof", literal="", consumed_len=0)
        word_rows: List[dict] = []
        adapted = 0
        encoded = 0
        unique_encoded = 0
        rank2 = 0
        rank3 = 0
        baseline_letters = 0
        best_cost_sum = 0

        collision_rows: List[dict] = []
        for code, cands in self.index.items():
            if len(cands) > 1:
                total_freq = sum(self.lexicon_freq.get(w, 1) for w in cands)
                top_freq = self.lexicon_freq.get(cands[0], 1)
                collision_rows.append({
                    "code": code,
                    "candidate_count": len(cands),
                    "total_freq": total_freq,
                    "top_word": cands[0],
                    "top_freq_share": top_freq / total_freq if total_freq else 0.0,
                    "candidates_preview": " ".join(cands[:20]),
                })
        collision_rows.sort(key=lambda r: (-r["candidate_count"], -r["total_freq"], r["code"]))

        for word, freq in sorted(self.lexicon_freq.items(), key=lambda kv: (-kv[1], kv[0])):
            res = self.best_word_result(word, eof)
            baseline = len(word)
            baseline_letters += baseline
            intrinsic_best = min(res.cost if res.mode == "encoded" else 10**9, baseline)
            best_cost_sum += intrinsic_best
            if res.mode == "encoded":
                encoded += 1
                if res.cost < baseline:
                    adapted += 1
                if res.candidate_count == 1:
                    unique_encoded += 1
                if res.rank is not None and res.rank <= 1:
                    rank2 += 1
                if res.rank is not None and res.rank <= 2:
                    rank3 += 1

            word_rows.append({
                "word": word,
                "freq": freq,
                "mode": res.mode,
                "best_code": res.code,
                "input_sequence_eof": res.input_sequence,
                "cost_eof": res.cost,
                "baseline_len": baseline,
                "saved_vs_baseline": baseline - res.cost if res.mode == "encoded" else 0,
                "rank": "" if res.rank is None else res.rank + 1,
                "candidate_count": res.candidate_count,
                "segments": " + ".join(res.segments),
                "candidates_preview": " ".join(res.candidates_preview),
            })

        summary = {
            "lexicon_size": len(self.lexicon_freq),
            "encoded_words": encoded,
            "adapted_words_cost_below_raw": adapted,
            "unique_encoded_words": unique_encoded,
            "rank2_or_better_encoded_words": rank2,
            "rank3_or_better_encoded_words": rank3,
            "baseline_letters": baseline_letters,
            "best_intrinsic_letters_eof": best_cost_sum,
            "intrinsic_letter_reduction_ratio_eof": (baseline_letters - best_cost_sum) / baseline_letters if baseline_letters else 0.0,
            "collision_code_count": len(collision_rows),
        }
        return word_rows, summary, collision_rows


def write_csv(path: str | Path, rows: List[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: str | Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
