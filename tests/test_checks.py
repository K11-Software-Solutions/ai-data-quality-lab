"""Each data-quality check, on small hand-made inputs and on the generated datasets."""
import pytest

from dqlab import checks
from dqlab.data import FACTS, VARIANTS, build, reword


def test_normalise_ignores_case_punctuation_and_ticket_numbers():
    assert checks.normalise("What IS the Plan? (ticket 12345)") == "what is the plan"


def test_jaccard_and_shingles():
    a = checks.shingles("the quick brown fox jumps")
    assert checks.jaccard(a, a) == 1.0
    assert checks.jaccard(a, checks.shingles("a completely different sentence here")) == 0.0


def test_contamination_exact_and_near():
    ev = [{"id": "e1", "question": "What is the free trial?"},
          {"id": "e2", "question": "How much is the Starter plan cost per month for my bakery?"},
          {"id": "e3", "question": "Something nobody trained on at all?"}]
    train = [{"id": "t1", "question": "what is the FREE trial (ticket 55555)"},
             {"id": "t2", "question": reword(ev[1]["question"])}]
    found = checks.contamination(ev, train)
    assert found["exact"] == ["e1"] and found["near"] == ["e2"]


def test_heavy_rewording_evades_both_exact_and_near_duplicate_checks():
    """A known limit of text-overlap checks: this leak is invisible to both (article 03)."""
    q = "What is the number of invoices on the Starter plan for my bakery?"
    assert checks.normalise(reword(q)) != checks.normalise(q)
    assert checks.jaccard(checks.shingles(q), checks.shingles(reword(q))) < 0.5


def test_schema_and_duplicates():
    rows = [{"id": "a", "question": "q?", "answer": "x", "fact": "trial_length", "topic": "billing", "lang": "en"},
            {"id": "a", "question": "Q?", "fact": "trial_length", "topic": "marketing", "lang": "en"}]
    problems = checks.schema(rows)
    assert any("'answer'" in p for p in problems) and any("unknown topic" in p for p in problems)
    assert any("duplicate id" in p for p in problems)
    assert checks.duplicates(rows) == ["a"]


@pytest.mark.parametrize("text, kind", [
    ("mail me at jo.smith@example.com", "email"),
    ("call +1 (415) 555-0100 today", "phone number"),
    ("card 4111 1111 1111 1111", "card number"),
])
def test_pii_detection(text, kind):
    assert checks.pii({"x": text}) == [f"x: {kind}"]


def test_pii_card_check_requires_luhn_and_the_phone_pattern_has_false_positives():
    found = checks.pii({"x": "Order 1234 5678 9012 3456 shipped"})
    assert "x: card number" not in found                  # 16 digits, but not Luhn-valid: not a card
    assert found == ["x: phone number"]                   # known false positive, documented in article 06
    assert checks.pii({"x": "Up to 25 employees and 12 regions"}) == []
    assert checks.luhn("4111111111111111") and not checks.luhn("4111111111111112")


def test_label_audit_uses_the_newest_document():
    corpus = [{"id": "old", "fact": "trial_length", "topic": "billing", "date": "2025-01-01",
               "text": "LedgerLite: The free trial is 14 days."},
              {"id": "new", "fact": "trial_length", "topic": "billing", "date": "2026-09-01",
               "text": "LedgerLite: The free trial is 30 days."}]
    rows = [{"id": "ok", "fact": "trial_length", "answer": "30 days"},
            {"id": "wrong", "fact": "trial_length", "answer": "14 days"}]
    assert checks.label_audit(rows, corpus) == ["wrong"]
    assert checks.corpus_health(corpus) == {"stale": ["old"], "contradictions": []}


def test_psi_is_zero_for_identical_mixes_and_grows_with_skew():
    a = {"x": 0.5, "y": 0.5}
    assert checks.psi(a, a) == 0
    assert checks.psi(a, {"x": 0.9, "y": 0.1}) > checks.psi(a, {"x": 0.6, "y": 0.4}) > 0


def test_fingerprint_changes_with_content():
    rows = [{"id": 1, "q": "a"}]
    assert checks.fingerprint(rows) == checks.fingerprint([{"q": "a", "id": 1}])     # key order does not matter
    assert checks.fingerprint(rows) != checks.fingerprint([{"id": 1, "q": "b"}])


def test_generator_is_deterministic_and_clean_by_default():
    a, b = build(), build()
    assert a == b
    assert checks.contamination(a["eval"], a["train"]) == {"exact": [], "near": []}
    assert not checks.duplicates(a["eval"]) and not checks.schema(a["eval"])
    assert checks.label_audit(a["eval"], a["corpus"]) == []
    assert all(r["answer"] == FACTS[r["fact"]][2] for r in a["eval"])


def test_unknown_variant_is_an_error():
    with pytest.raises(ValueError):
        build("perfect-data")
    assert "" in VARIANTS
