"""Data-quality checks. Each returns findings (a list of problems), so they can be gated.

contamination       eval items that also appear in training data: exact (after normalising)
                    and near-duplicate (word-shingle Jaccard similarity)
duplicates          the same eval question more than once
schema              required fields, allowed values, unique ids
label_audit         reference answers that disagree with the knowledge source (the corpus)
pii                 emails, phone numbers and Luhn-valid card numbers in text
corpus_health       stale (superseded) documents and contradictions between documents
coverage            share of production topics that the corpus has documents for
representativeness  eval mix against production mix (topic and language), as PSI
fingerprint         content hash of each dataset, to pin which data a result came from
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict

from dqlab.data import TOPICS

TICKET = re.compile(r"\(ticket \d+\)")


def normalise(text: str) -> str:
    text = TICKET.sub("", text.lower())
    return " ".join(re.findall(r"[a-z0-9]+", text))


def shingles(text: str, n: int = 3) -> set[tuple]:
    words = normalise(text).split()
    return {tuple(words[i:i + n]) for i in range(max(1, len(words) - n + 1))}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a or b else 1.0


def contamination(eval_rows: list[dict], train: list[dict], threshold: float = 0.5) -> dict:
    """Eval questions found in the training data, exactly or nearly."""
    train_norm = {normalise(t["question"]) for t in train}
    train_sh = [shingles(t["question"]) for t in train]
    exact, near = [], []
    for r in eval_rows:
        if normalise(r["question"]) in train_norm:
            exact.append(r["id"])
            continue
        s = shingles(r["question"])
        if any(jaccard(s, t) >= threshold for t in train_sh):
            near.append(r["id"])
    return {"exact": exact, "near": near}


def duplicates(eval_rows: list[dict]) -> list[str]:
    seen, dups = {}, []
    for r in eval_rows:
        key = (normalise(r.get("question", "")), r.get("lang"))
        if key in seen:
            dups.append(r["id"])
        seen[key] = r["id"]
    return dups


SCHEMA = {"id": str, "question": str, "answer": str, "fact": str, "topic": str, "lang": str}


def schema(eval_rows: list[dict]) -> list[str]:
    problems, ids = [], Counter(r.get("id") for r in eval_rows)
    for r in eval_rows:
        for field, kind in SCHEMA.items():
            if not isinstance(r.get(field), kind) or r.get(field) == "":
                problems.append(f"{r.get('id')}: missing or invalid '{field}'")
        if r.get("topic") not in TOPICS:
            problems.append(f"{r.get('id')}: unknown topic '{r.get('topic')}'")
    problems += [f"{i}: duplicate id" for i, n in ids.items() if n > 1]
    return problems


def current_facts(corpus: list[dict]) -> dict[str, str]:
    """The newest document per fact is the source of truth."""
    newest: dict[str, dict] = {}
    for d in corpus:
        if d.get("fact") and (d["fact"] not in newest or d["date"] > newest[d["fact"]]["date"]):
            newest[d["fact"]] = d
    return {k: d["text"] for k, d in newest.items()}


def label_audit(eval_rows: list[dict], corpus: list[dict]) -> list[str]:
    """Reference answers not supported by the current document for their fact."""
    truth = current_facts(corpus)
    return [r["id"] for r in eval_rows if r.get("fact") in truth and r.get("answer", "").lower() not in truth[r["fact"]].lower()]


EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
PHONE = re.compile(r"(?<!\w)\+?\d[\d ()-]{8,}\d(?!\w)")
CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def luhn(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch) * (2 if alt else 1)
        total += d - 9 if d > 9 else d
        alt = not alt
    return total % 10 == 0


def pii(texts: dict[str, str]) -> list[str]:
    """{id: text} -> findings. Card numbers count only if they pass the Luhn check."""
    out = []
    for i, t in texts.items():
        if EMAIL.search(t):
            out.append(f"{i}: email")
        cards = [re.sub(r"\D", "", m.group()) for m in CARD.finditer(t)]
        if any(13 <= len(c) <= 19 and luhn(c) for c in cards):
            out.append(f"{i}: card number")
        elif PHONE.search(t):
            out.append(f"{i}: phone number")
    return out


def corpus_health(corpus: list[dict]) -> dict:
    by_fact = defaultdict(list)
    for d in corpus:
        if d.get("fact"):
            by_fact[d["fact"]].append(d)
    stale, contradictions = [], []
    for fact, docs in by_fact.items():
        newest = max(d["date"] for d in docs)
        stale += [d["id"] for d in docs if d["date"] < newest]
        current = [d for d in docs if d["date"] == newest]
        values = {re.sub(r"^[^:]*:\s*", "", d["text"]).lower() for d in current}
        if len(values) > 1:
            contradictions.append(fact)
    return {"stale": stale, "contradictions": contradictions}


def coverage(corpus: list[dict], production: list[dict]) -> float:
    covered = {d["topic"] for d in corpus}
    return sum(p["topic"] in covered for p in production) / len(production)


def psi(expected: dict, actual: dict, floor: float = 1e-4) -> float:
    """Population stability index between two distributions over the same categories."""
    keys = set(expected) | set(actual)
    return sum((max(actual.get(k, 0), floor) - max(expected.get(k, 0), floor))
               * math.log(max(actual.get(k, 0), floor) / max(expected.get(k, 0), floor)) for k in keys)


def mix(rows: list[dict], field: str) -> dict:
    c = Counter(r.get(field) for r in rows)
    return {k: v / len(rows) for k, v in c.items()}


def representativeness(eval_rows: list[dict], production: list[dict]) -> dict:
    return {"topic_psi": psi(mix(production, "topic"), mix(eval_rows, "topic")),
            "lang_psi": psi(mix(production, "lang"), mix(eval_rows, "lang"))}


def fingerprint(rows: list[dict]) -> str:
    blob = "\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]
