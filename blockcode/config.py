from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List

from .model import Rule, Scope, Settings, CommitModel


def parse_bool(s: str) -> bool:
    return str(s).strip().lower() in {"1", "true", "yes", "y", "on", "enabled"}


def load_settings(path: str | Path) -> Settings:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cm = data.get("commit_model", {})
    commit = CommitModel(
        rank1_key=str(cm.get("rank1_key", ";")),
        rank2_key=str(cm.get("rank2_key", "'")),
        bare_commit_cost=int(cm.get("bare_commit_cost", 1)),
        eof_rank0_commit_cost=int(cm.get("eof_rank0_commit_cost", 0)),
        punctuation_committers=tuple(cm.get("punctuation_committers", [",", ".", "?", "!", ":", ";"])),
        auto_consume_space_after_punctuation=bool(cm.get("auto_consume_space_after_punctuation", True)),
        rank_selection_consumes_space_boundary=bool(cm.get("rank_selection_consumes_space_boundary", True)),
    )
    return Settings(
        literal_letter_fallback=bool(data.get("literal_letter_fallback", True)),
        raw_prefix_cost=int(data.get("raw_prefix_cost", 1)),
        max_encoded_word_len=int(data.get("max_encoded_word_len", 48)),
        uppercase_extra_cost=int(data.get("uppercase_extra_cost", 1)),
        unknown_char_cost=int(data.get("unknown_char_cost", 1)),
        selection_costs=tuple(int(x) for x in data.get("selection_costs", [0, 1, 2, 2, 3])),
        unlisted_rank_cost=int(data.get("unlisted_rank_cost", 99)),
        candidate_preview=int(data.get("candidate_preview", 10)),
        max_candidate_rank=int(data.get("max_candidate_rank", 3)),
        commit_model=commit,
    )


def load_rules_tsv(path: str | Path, enabled_only: bool = True) -> List[Rule]:
    rules: List[Rule] = []
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        required = {"rule_id", "chunk", "code", "scope", "class", "enabled"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"rules TSV missing columns: {sorted(missing)}")
        for row in reader:
            if not row or not row.get("chunk"):
                continue
            enabled = parse_bool(row.get("enabled", "1"))
            if enabled_only and not enabled:
                continue
            scope = Scope(str(row.get("scope", "any")).strip().lower())
            rule = Rule(
                rule_id=str(row.get("rule_id", "")).strip(),
                chunk=str(row.get("chunk", "")).strip().lower(),
                code=str(row.get("code", "")).strip().lower(),
                scope=scope,
                cls=str(row.get("class", "")).strip(),
                enabled=enabled,
                group=str(row.get("group", "")).strip(),
                note=str(row.get("note", "")).strip(),
            )
            if not rule.chunk or not rule.code:
                continue
            rules.append(rule)
    rules.sort(key=lambda r: (-len(r.chunk), r.chunk, r.code, r.scope.value, r.rule_id))
    return rules


def write_rules_tsv(path: str | Path, rules: list[Rule]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["rule_id", "chunk", "code", "scope", "class", "enabled", "group", "note"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for r in rules:
            writer.writerow({
                "rule_id": r.rule_id,
                "chunk": r.chunk,
                "code": r.code,
                "scope": r.scope.value,
                "class": r.cls,
                "enabled": "1" if r.enabled else "0",
                "group": r.group,
                "note": r.note,
            })
