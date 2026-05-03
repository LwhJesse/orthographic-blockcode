from pathlib import Path

from blockcode.config import load_rules_tsv, load_settings
from blockcode.lexicon import load_lexicon
from blockcode.evaluator import Evaluator
from blockcode.model import DelimiterInfo


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


def test_raw_fallback_comparison_includes_following_delimiter_cost():
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(root / "configs/settings_default.json")
    rules = load_rules_tsv(root / "configs/rules_v1.tsv")
    lex = load_lexicon(root / "data/examples/mini_lexicon.tsv")
    ev = Evaluator(rules, settings, lex)

    # Candidate order for code `su` is see, sea, su. For `su, ` the encoded
    # third-candidate path should beat raw fallback once the following comma
    # and space are counted in the comparison frame.
    delim = DelimiterInfo(kind="punct", literal=",", consumed_len=2, auto_consumed_space=True)
    res = ev.best_word_result("su", delim)

    assert res.mode == "encoded"
    assert res.code == "su"
    assert res.rank == 2
    assert res.cost == 4


def test_non_ascii_literals_count_per_character():
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(root / "configs/settings_default.json")
    rules = load_rules_tsv(root / "configs/rules_v1.tsv")
    lex = load_lexicon(root / "data/examples/mini_lexicon.tsv")
    ev = Evaluator(rules, settings, lex)

    rows, summary = ev.evaluate_text("你好，世界")

    assert summary["baseline_total"] == len("你好，世界")
    assert summary["total_cost"] == len("你好，世界")
    assert all(row["type"] == "literal" for row in rows)
