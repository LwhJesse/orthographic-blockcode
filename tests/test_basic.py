from pathlib import Path

from blockcode.config import load_rules_tsv, load_settings
from blockcode.lexicon import load_lexicon
from blockcode.evaluator import Evaluator


def test_sample_evaluates():
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(root / "configs/settings_default.json")
    rules = load_rules_tsv(root / "configs/rules_v1.tsv")
    text = (root / "data/examples/sample_article.txt").read_text(encoding="utf-8")
    lex = load_lexicon(root / "data/examples/mini_lexicon.tsv")
    ev = Evaluator(rules, settings, lex)
    rows, summary = ev.evaluate_text(text)
    assert summary["word_count"] > 0
    assert summary["total_cost"] > 0
    assert rows
