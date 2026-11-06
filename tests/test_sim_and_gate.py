"""What data problems do to measured numbers, and the gate's negative controls."""
import json

import pytest

from dqlab import checks, sim
from dqlab.data import build, load
from evals import run_data_checks as gate


def test_contamination_inflates_measured_accuracy():
    clean, leaked = build(), build("contaminated", leak_share=0.3)
    acc = lambda d: sum(sim.score_model(d["eval"], d["train"], s)["accuracy"] for s in range(5)) / 5
    assert acc(leaked) > acc(clean) + 0.05


def test_near_duplicate_check_catches_more_reworded_leaks_than_exact_matching():
    d = build("contaminated")
    found = checks.contamination(d["eval"], d["train"])
    reworded = set(d["meta"]["leaked_reworded"])
    verbatim = set(d["meta"]["leaked_verbatim"])
    assert verbatim <= set(found["exact"])
    assert len(reworded & (set(found["exact"]) | set(found["near"]))) > len(reworded & set(found["exact"]))


def test_wrong_labels_are_found_by_the_audit():
    d = build("noisy-labels")
    assert set(checks.label_audit(d["eval"], d["corpus"])) == set(d["meta"]["noisy"])


def test_reweighting_recovers_production_accuracy_from_a_skewed_eval():
    d = build("skewed-eval")
    s = sim.score_model(d["eval"], d["train"])
    prod = sim.production_accuracy()
    assert abs(s["accuracy"] - prod) > 0.08
    assert abs(sim.reweighted(s["per_topic"]) - prod) < 0.03


def test_newest_first_retrieval_fixes_stale_but_not_contradictory_documents():
    stale, contra = build("stale-corpus")["corpus"], build("contradictory")["corpus"]
    assert sim.rag_accuracy(build()["corpus"]) == 1.0
    assert sim.rag_accuracy(stale) < 0.9 and sim.rag_accuracy(stale, newest_first=True) == 1.0
    assert sim.rag_accuracy(contra, newest_first=True) < 0.9


def test_committed_data_matches_the_generator():
    """The committed files cannot drift silently from the code that defines them."""
    built = build()
    assert load() == {k: v for k, v in built.items() if k != "meta"}


@pytest.mark.parametrize("variant, expected", [
    ("", None), ("contaminated", "contamination"), ("noisy-labels", "label_audit"),
    ("skewed-eval", "representativeness"), ("stale-corpus", "stale_documents"), ("contradictory", "contradictions"),
    ("pii-leak", "pii"), ("schema-break", "schema"), ("duplicate-eval", "eval_duplicates"),
])
def test_negative_controls(monkeypatch, tmp_path, variant, expected):
    monkeypatch.setenv("DATA_VARIANT", variant)
    code = gate.main(["--out", str(tmp_path)])
    failures = json.loads((tmp_path / "data_report.json").read_text(encoding="utf-8"))["gate_failures"]
    if expected is None:
        assert code == 0 and failures == []
    else:
        assert code == 1 and any(f.startswith(expected) for f in failures), failures
