"""What data problems do to the numbers people make decisions with.

score_model      a model's measured accuracy on an eval set. The model answers a question it
                 saw (nearly) verbatim in training correctly 98% of the time (memorisation);
                 otherwise it is right with the probability for that topic (its real skill).
                 Answers are graded against the eval set's reference answer, so a wrong
                 reference turns a right answer into a "miss" and vice versa.
production_accuracy  the same model's true accuracy on the production topic mix
reweighted       eval accuracy per topic, weighted by the production mix
rag_accuracy     a RAG answer is right if the document it retrieves for the fact is current
                 and agrees with the truth; retrieval picks among the documents for a fact
                 either at random or preferring the newest
"""
from __future__ import annotations

import random
import re
from collections import defaultdict

from dqlab.checks import jaccard, normalise, shingles
from dqlab.data import FACTS, PRODUCTION_MIX, SKILL

MEMORISED = 0.98


def memorised_ids(eval_rows: list[dict], train: list[dict], threshold: float = 0.7) -> set[str]:
    """Which eval items the model has effectively seen: exact or very close matches in training."""
    norm = {normalise(t["question"]) for t in train}
    sh = [shingles(t["question"]) for t in train]
    out = set()
    for r in eval_rows:
        if normalise(r["question"]) in norm or any(jaccard(shingles(r["question"]), s) >= threshold for s in sh):
            out.add(r["id"])
    return out


def score_model(eval_rows: list[dict], train: list[dict], seed: int = 0, skill_shift: float = 0.0,
                memorised: set[str] | None = None) -> dict:
    rng = random.Random(seed)
    seen = memorised if memorised is not None else memorised_ids(eval_rows, train)
    per_topic = defaultdict(list)
    for r in eval_rows:
        p = MEMORISED if r["id"] in seen else min(1.0, SKILL[r["topic"]] + skill_shift)
        answer = FACTS[r["fact"]][2] if rng.random() < p else "something else"
        per_topic[r["topic"]].append(answer == r["answer"])
    all_ = [x for v in per_topic.values() for x in v]
    return {"accuracy": sum(all_) / len(all_), "per_topic": {t: sum(v) / len(v) for t, v in per_topic.items()}}


def production_accuracy(skill_shift: float = 0.0) -> float:
    return sum(w * min(1.0, SKILL[t] + skill_shift) for t, w in PRODUCTION_MIX.items())


def reweighted(per_topic: dict[str, float], mix: dict[str, float] = PRODUCTION_MIX) -> float:
    covered = {t: w for t, w in mix.items() if t in per_topic}
    total = sum(covered.values())
    return sum(per_topic[t] * w / total for t, w in covered.items())


def _value(doc_text: str) -> str:
    # the value follows the LAST " is ": subjects can contain one ("how long deleted data is kept")
    return re.sub(r"^[^:]*:\s*", "", doc_text).rsplit(" is ", 1)[-1].rstrip(".").lower()


def rag_accuracy(corpus: list[dict], questions: int = 1000, newest_first: bool = False, seed: int = 0) -> float:
    rng = random.Random(seed)
    by_fact = defaultdict(list)
    for d in corpus:
        if d.get("fact"):
            by_fact[d["fact"]].append(d)
    right = 0
    for _ in range(questions):
        fact = rng.choice(list(FACTS))
        docs = by_fact[fact]
        if newest_first:
            newest = max(d["date"] for d in docs)
            docs = [d for d in docs if d["date"] == newest]
        right += _value(rng.choice(docs)["text"]) == FACTS[fact][2].lower()
    return right / questions
