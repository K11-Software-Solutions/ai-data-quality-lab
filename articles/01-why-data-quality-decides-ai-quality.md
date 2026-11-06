# 01. Why Data Quality Decides AI Quality

> **Series:** AI Data Quality Lab · [Index](../README.md#articles) · Next: [02. Four Datasets and What Hides in Them](02-four-datasets-and-what-hides-in-them.md)

This is the eighth lab in a series for quality engineers moving into AI. The earlier labs tested applications, models, agents, teams of agents, performance and evaluators. Under all of them sits **data**: what the model learned from, what it retrieves, and what it is measured against. When the data is wrong, every test built on it is wrong in the same direction, and nothing downstream can tell.

## Three ways data fails an AI system

| The data | What goes wrong | What it does to your numbers |
|---|---|---|
| **Training or fine-tuning data** | contains your eval questions (contamination), or personal data | eval scores look better than the model is; privacy exposure |
| **Eval sets** | wrong reference answers (label noise), duplicates, broken rows, a mix of questions unlike production | scores are biased, noisy, or about the wrong users |
| **The RAG corpus** | outdated documents, documents that contradict each other, gaps, personal data | the app gives wrong answers with confidence, and leaks |

What makes these failures dangerous is that **they do not look like failures**. A contaminated eval set produces a higher score. A skewed eval set produces a higher score. A stale document produces a fluent, well-grounded, wrong answer that every groundedness check passes, because the answer really is in the retrieved document.

## Testing data like code

Quality engineers already know how to do this for application data: schemas, constraints, uniqueness, reference checks, versioning. This lab applies the same discipline to AI data, with checks designed for AI's specific failure modes:

| Check | Finds | Article |
|---|---|---|
| exact and near-duplicate matching between eval and training data | contamination | 03 |
| reference answers checked against the knowledge source | wrong labels | 04 |
| topic and language mix compared with production | an unrepresentative eval set | 05 |
| version dates and agreement across documents; PII patterns | stale and contradictory documents; personal data | 06 |
| schema, uniqueness, and pinned content fingerprints | broken rows, duplicates, unreviewed data changes | 07 |

Each check runs in CI on the lab's committed datasets, and each one is proven by a **negative control**: a version of the data with one known problem injected, which the gate must reject (article 08).

## Why synthetic data

The lab's data describes **LedgerLite**, a fictional accounting app. Everything is generated from a fact table and templates, deterministically. That gives two things real data cannot: every problem can be injected at a known size, and the ground truth (which items were leaked, which labels are wrong) is known, so the checks themselves can be measured: how many problems they find, how many they miss, and what each problem does to the numbers people use to make decisions.
