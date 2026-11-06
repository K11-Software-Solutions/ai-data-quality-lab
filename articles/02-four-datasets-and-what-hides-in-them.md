# 02. Four Datasets and What Hides in Them

> **Series:** AI Data Quality Lab · [Index](../README.md#articles) · Previous: [01](01-why-data-quality-decides-ai-quality.md) · Next: [03. Contamination](03-contamination-when-the-test-is-in-the-training-data.md)

## The datasets

[`dqlab/data.py`](../dqlab/data.py) generates four files in [`data/`](../data), as an AI team would have them:

| File | Rows | What it is |
|---|---|---|
| `train.jsonl` | 1,200 | fine-tuning examples taken from support tickets: same facts as the eval set, phrased as tickets |
| `eval.jsonl` | 300 | the held-out eval set: question, reference answer, the fact it tests, topic, language |
| `corpus.jsonl` | 21 | the RAG corpus: one document per fact (with a date) and one how-to page per topic |
| `production.jsonl` | 1,000 | a sample of real user questions from logs: topic and language only |

All of it is about 15 facts of a fictional product, LedgerLite: prices, limits, supported banks, security settings, each with a **current** value and an **older** one. The older values are what make stale documents and wrong labels realistic: a wrong answer is usually last year's right answer.

Topics differ in difficulty for the model: it answers billing questions it has not memorised correctly 85% of the time, tax questions 45%. Production traffic has more payroll and tax questions than the average eval set would naturally get.

## Problems you can inject

`build(variant)` produces the same datasets with one known problem:

| Variant | The problem |
|---|---|
| `contaminated` | eval questions copied into the training data: half verbatim, half lightly reworded |
| `noisy-labels` | 8% of reference answers replaced by the older (wrong) value |
| `skewed-eval` | the eval set over-represents easy topics and English |
| `stale-corpus` | outdated versions of five facts left in the corpus |
| `contradictory` | four current-dated documents that disagree with the main ones |
| `pii-leak` | an email, a phone number and a card number in documents, and an email in an eval question |
| `schema-break` | eval rows with a missing answer, an unknown topic and a duplicate id |
| `duplicate-eval` | thirty questions repeated in the eval set |

`build` also returns the ground truth (which items were leaked, which labels are wrong), which the experiments use to measure the checks.

## The model and the RAG app

[`dqlab/sim.py`](../dqlab/sim.py) stands in for the AI system:

- **The model** answers a question it saw (nearly) verbatim in training correctly 98% of the time: memorisation. Otherwise it is right with its real skill for that topic. Answers are graded against the eval set's reference answer, so a wrong reference turns a right answer into a miss.
- **The RAG app** answers a question from a document retrieved for the fact: right if that document is current and agrees with the truth. Retrieval picks among the documents for a fact either at random or preferring the newest.

That is enough to show what each data problem does to the numbers people make decisions with: measured accuracy, the gap between two models, the production estimate, and RAG answer accuracy.

## Running the checks

```bash
python -m evals.run_data_checks                           # the committed data
DATA_VARIANT=stale-corpus python -m evals.run_data_checks    # with one problem: must fail
```
