# 06. RAG Corpus Health and Privacy

> **Series:** AI Data Quality Lab · [Index](../README.md#articles) · Previous: [05](05-representativeness-does-the-eval-look-like-production.md) · Next: [07. Data Contracts and Versioning](07-data-contracts-and-versioning.md)

A RAG application is only as correct as the documents it retrieves. When the corpus is wrong, the app is wrong **with evidence**: its answer really is in the retrieved document, so groundedness checks pass, citations look right, and the user has every reason to believe it.

## Stale and contradictory documents

Two problems account for most corpus errors:

- **Stale documents**: an old version of a page that was never removed. Last year's price page next to this year's.
- **Contradictions**: two current documents that disagree. The pricing page says one thing, an FAQ says another.

The corpus check finds both mechanically: for each fact, any document older than the newest is **stale**; any disagreement among the newest documents is a **contradiction**.

Experiment E4 asks 1,000 questions of the RAG app:

| Corpus | Found by the check | Random retrieval | Newest-first retrieval | After removing stale documents |
|---|---|---|---|---|
| clean | nothing | 100% | 100% | 100% |
| 5 stale documents | 5 stale | **84.4%** | 100% | 100% |
| 4 contradicting documents | 4 contradictions | **86.4%** | **86.4%** | **86.4%** |

**Date-aware retrieval fixes staleness but not contradictions.** Preferring the newest document removes the stale ones from consideration, but contradicting documents are equally new, so the app still picks the wrong one about half the time for those facts. Only a person can decide which document is right; the check's job is to find the conflict and block the release until someone does.

This needs **metadata**: a fact or topic key and a reliable date for every document. Corpora without them can still be checked, by extracting claims and comparing them, but far less reliably. Adding dates and ownership to documents is often the most valuable data-quality change a RAG team can make.

## Coverage

The corpus must also contain what users ask about. The check computes the share of production questions whose topic has at least one document, and the gate requires 95%. A topic users ask about with no document produces either a refusal or, worse, an answer from the model's general knowledge.

## Personal data

Corpora are built from real documents, and real documents contain people: support transcripts, exported tickets, attachments. Eval sets built from production traffic contain them too. The PII check looks for:

| Pattern | How |
|---|---|
| email addresses | pattern |
| phone numbers | international and local formats |
| card numbers | 13 to 19 digits that pass the **Luhn** checksum |

The Luhn check matters: without it, every long number (order IDs, invoice numbers) looks like a card. Even so, the phone pattern has a known false positive the test suite keeps on record: an order number written in groups of four ("1234 5678 9012 3456") is flagged as a phone number. Pattern-based detection trades recall against precision; production systems combine patterns with context (a nearby word like "phone"), named-entity models, and human review of a sample.

The gate fails on any PII found in the corpus, the eval set or the training data. The right response is to redact at the source, not to filter at query time: a document with a customer's card number should never be retrievable.

## Takeaways

- **A wrong document produces a confident, grounded, wrong answer.**
- **Prefer the newest document to fix staleness; contradictions need a person.**
- **Give every document a key and a date**, or none of this can be checked.
- **Gate on PII in every dataset, and redact at the source.** Use checksums to keep false positives down.
