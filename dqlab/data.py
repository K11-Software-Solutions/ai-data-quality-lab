"""Synthetic data for a fictional product, LedgerLite (a small-business accounting app).

Four datasets, as an AI team would have them:

    train.jsonl        question/answer pairs used to fine-tune the model
    eval.jsonl         the held-out eval set: question, reference answer, topic, language
    corpus.jsonl       the RAG corpus: one fact per document, with a version date
    production.jsonl   a sample of real user questions (topic and language), from logs

Everything is generated from a fact table and question templates, deterministically.
`build(variant)` can inject one known data problem, which is how the lab tests its checks:

    contaminated   eval questions copied into training data: half verbatim, half reworded
    noisy-labels   8% of eval reference answers replaced by a wrong value
    skewed-eval    the eval set over-represents easy topics and English
    stale-corpus   outdated versions of facts left in the corpus
    contradictory  documents that disagree with each other about the same fact
    pii-leak       customer emails, phone numbers and card numbers inside documents and eval items
    schema-break   eval rows with missing fields, unknown topics and duplicate ids
    duplicate-eval the same question several times in the eval set
"""
from __future__ import annotations

import json
import random
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
TOPICS = ("billing", "invoices", "payroll", "tax", "bank-sync", "security")
LANGS = ("en", "es", "de")

# fact key: (topic, subject phrase, current value, older value)
FACTS = {
    "plan_price": ("billing", "the Starter plan cost per month", "12 dollars", "9 dollars"),
    "annual_discount": ("billing", "the discount for paying annually", "20 percent", "15 percent"),
    "trial_length": ("billing", "the free trial", "30 days", "14 days"),
    "invoice_limit": ("invoices", "the number of invoices on the Starter plan", "50 per month", "25 per month"),
    "invoice_currency": ("invoices", "the number of invoice currencies supported", "40 currencies", "25 currencies"),
    "invoice_reminders": ("invoices", "automatic payment reminders", "every 7 days", "every 14 days"),
    "payroll_staff": ("payroll", "the number of employees payroll supports", "up to 25 employees", "up to 10 employees"),
    "payroll_runs": ("payroll", "payroll runs per month", "unlimited runs", "2 runs"),
    "tax_regions": ("tax", "the number of tax regions supported", "12 regions", "8 regions"),
    "tax_filing": ("tax", "the quarterly filing deadline reminder", "10 days before the deadline", "5 days before the deadline"),
    "bank_count": ("bank-sync", "the number of banks that sync", "over 9,000 banks", "over 5,000 banks"),
    "bank_refresh": ("bank-sync", "how often bank transactions refresh", "every 4 hours", "once a day"),
    "mfa_methods": ("security", "the two-factor methods offered", "authenticator apps and security keys", "SMS codes"),
    "session_timeout": ("security", "the idle session timeout", "30 minutes", "60 minutes"),
    "data_retention": ("security", "how long deleted data is kept", "30 days", "90 days"),
}
TEMPLATES = (
    "What is {s}?", "Can you tell me {s}?", "How much is {s}?", "I need to know {s}.",
    "Quick question: what's {s}?", "Remind me about {s}.", "Do you know {s} in LedgerLite?",
    "What's the current figure for {s}?", "Could someone confirm {s}?", "Where can I check {s}?",
    "Has anything changed about {s}?", "Help me understand {s}.",
)
CONTEXTS = ("", " for my bakery", " for a freelancer", " for our team", " on the mobile app", " for my shop",
            " for a nonprofit", " this year", " for my agency", " for a new account")
# Training data comes from support tickets: same facts, different phrasing from the eval set.
TRAIN_TEMPLATES = (
    "Customer wrote in after upgrading and was unsure about {s}; the agent explained it",
    "Ticket from a small business owner asking our team to clarify {s} before renewing",
    "Chat transcript: user compared plans and wanted details on {s} for their accountant",
    "Email thread where a bookkeeper double-checked {s} while onboarding a new client",
    "Support call summary: the caller had seen conflicting information about {s}",
    "Forum post answered by staff explaining {s} to a confused new user",
)
# Light rewording used to hide contamination from exact-match checks.
REWORD = {"What is": "Tell me", "Can you tell me": "Could you say", "the": "", "number of": "count of",
          "How much is": "What's", "I need to know": "Please share", "Quick question:": "Hi,"}
# Topic difficulty: share of unseen questions the model answers correctly.
SKILL = {"billing": 0.85, "invoices": 0.80, "payroll": 0.55, "tax": 0.45, "bank-sync": 0.70, "security": 0.75}
PRODUCTION_MIX = {"billing": 0.20, "invoices": 0.15, "payroll": 0.20, "tax": 0.20, "bank-sync": 0.15, "security": 0.10}
PRODUCTION_LANGS = {"en": 0.6, "es": 0.25, "de": 0.15}
VARIANTS = ("", "contaminated", "noisy-labels", "skewed-eval", "stale-corpus", "contradictory", "pii-leak",
            "schema-break", "duplicate-eval")


def question(key: str, template: int, context: int = 0) -> str:
    q = TEMPLATES[template % len(TEMPLATES)].format(s=FACTS[key][1])
    ctx = CONTEXTS[context % len(CONTEXTS)]
    return q[:-1] + ctx + q[-1] if ctx else q


def reword(text: str) -> str:
    out = text
    for a, b in REWORD.items():
        out = out.replace(a + " ", (b + " ") if b else "")
    return " ".join(out.split())


def _pick(rng: random.Random, mix: dict) -> str:
    return rng.choices(list(mix), list(mix.values()))[0]


def build(variant: str = "", seed: int = 0, leak_share: float = 0.2, noise_share: float = 0.08) -> dict:
    """The four datasets, plus "meta": the ground truth about what was injected (never written to disk)."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant '{variant}'")
    rng = random.Random(seed)
    meta = {"leaked_verbatim": [], "leaked_reworded": [], "noisy": []}
    keys_by_topic = {t: [k for k, f in FACTS.items() if f[0] == t] for t in TOPICS}

    # Eval set: 300 items, production-like mix (or skewed), one template per (key, template, language)
    eval_mix = ({"billing": 0.45, "invoices": 0.30, "security": 0.15, "bank-sync": 0.05, "payroll": 0.03, "tax": 0.02}
                if variant == "skewed-eval" else PRODUCTION_MIX)
    eval_langs = {"en": 0.95, "es": 0.05, "de": 0.0} if variant == "skewed-eval" else PRODUCTION_LANGS
    seen, eval_rows = set(), []
    while len(eval_rows) < 300:
        topic = _pick(rng, eval_mix)
        key = rng.choice(keys_by_topic[topic])
        lang = _pick(rng, eval_langs)
        t, c = rng.randrange(len(TEMPLATES)), rng.randrange(len(CONTEXTS))
        if (key, t, c) in seen:
            continue
        seen.add((key, t, c))
        eval_rows.append({"id": f"e{len(eval_rows):03d}", "question": question(key, t, c), "answer": FACTS[key][2],
                          "fact": key, "topic": topic, "lang": lang})
    if variant == "duplicate-eval":
        for i in range(0, 30):
            eval_rows[150 + i] = {**eval_rows[i], "id": eval_rows[150 + i]["id"]}
    if variant == "noisy-labels":
        for row in rng.sample(eval_rows, round(noise_share * len(eval_rows))):
            row["answer"] = FACTS[row["fact"]][3]                     # a plausible but wrong value
            meta["noisy"].append(row["id"])
    if variant == "schema-break":
        eval_rows[3].pop("answer")
        eval_rows[7]["topic"] = "marketing"
        eval_rows[11]["id"] = eval_rows[10]["id"]

    # Training data: questions about the same facts, but never the eval questions themselves
    eval_questions = {r["question"] for r in eval_rows}
    train = []
    for i in range(1200):
        key = rng.choice(list(FACTS))
        q = TRAIN_TEMPLATES[rng.randrange(len(TRAIN_TEMPLATES))].format(s=FACTS[key][1])
        q = f"{q} (ticket {rng.randrange(10_000, 99_999)})"            # real training data carries context
        train.append({"id": f"t{i:04d}", "question": q, "answer": FACTS[key][2]})
    if variant == "contaminated":
        leaked = rng.sample(eval_rows, round(leak_share * len(eval_rows)))
        for j, row in enumerate(leaked):
            q = row["question"] if j % 2 == 0 else reword(row["question"])
            meta["leaked_verbatim" if j % 2 == 0 else "leaked_reworded"].append(row["id"])
            train.append({"id": f"t-leak{j:02d}", "question": q, "answer": row["answer"]})
    del eval_questions

    # RAG corpus: one current document per fact, plus how-to documents
    corpus = [{"id": f"d-{k}", "fact": k, "topic": f[0], "date": "2026-09-01",
               "text": f"LedgerLite: {f[1][0].upper() + f[1][1:]} is {f[2]}."} for k, f in FACTS.items()]
    corpus += [{"id": f"d-howto-{t}", "fact": None, "topic": t, "date": "2026-08-15",
                "text": f"How to get started with {t.replace('-', ' ')} in LedgerLite: open Settings and choose {t}."}
               for t in TOPICS]
    if variant == "stale-corpus":
        for k in list(FACTS)[:5]:
            f = FACTS[k]
            corpus.append({"id": f"d-{k}-2025", "fact": k, "topic": f[0], "date": "2025-03-01",
                           "text": f"LedgerLite: {f[1][0].upper() + f[1][1:]} is {f[3]}."})
    if variant == "contradictory":
        for k in list(FACTS)[5:9]:
            f = FACTS[k]
            corpus.append({"id": f"d-{k}-faq", "fact": k, "topic": f[0], "date": "2026-09-01",
                           "text": f"FAQ: {f[1][0].upper() + f[1][1:]} is {f[3]}."})
    if variant == "pii-leak":
        corpus[2]["text"] += " Contact jane.doe@example.com or +44 20 7946 0958 for help."
        corpus[4]["text"] += " Card on file: 4111 1111 1111 1111."
        eval_rows[5]["question"] += " My email is sam.lee@example.org."

    # Production sample: what users actually ask about
    production = [{"id": f"p{i:04d}", "topic": _pick(rng, PRODUCTION_MIX), "lang": _pick(rng, PRODUCTION_LANGS)}
                  for i in range(1000)]
    return {"train": train, "eval": eval_rows, "corpus": corpus, "production": production, "meta": meta}


def write(datasets: dict[str, list[dict]], folder: Path = DATA) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for name, rows in datasets.items():
        if name == "meta":
            continue
        (folder / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                              encoding="utf-8")


def load(folder: Path = DATA) -> dict[str, list[dict]]:
    return {name: [json.loads(line) for line in (folder / f"{name}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
            for name in ("train", "eval", "corpus", "production")}


if __name__ == "__main__":
    write(build())
    print("wrote", ", ".join(f"{k}.jsonl" for k in ("train", "eval", "corpus", "production")), "to", DATA)
