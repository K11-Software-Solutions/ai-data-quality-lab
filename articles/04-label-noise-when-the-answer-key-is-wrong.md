# 04. Label Noise: When the Answer Key Is Wrong

> **Series:** AI Data Quality Lab · [Index](../README.md#articles) · Previous: [03](03-contamination-when-the-test-is-in-the-training-data.md) · Next: [05. Representativeness](05-representativeness-does-the-eval-look-like-production.md)

Every eval set has some wrong reference answers. They come from typos, from labellers who misread the source, and most often from **facts that changed**: the reference says the trial is 14 days because it was, when the set was written. A wrong reference marks a right answer as wrong.

## What wrong labels do

Experiment E2 compares two models, where model B is truly 5 points better than model A, on the 300-item eval set with 0 to 15% wrong references, 200 trials each:

| Wrong references | Measured gap | Eval picks the better model |
|---|---|---|
| 0% | 4.8 points | 91% |
| 4% | 4.7 | 92% |
| 8% | 4.4 | 90% |
| 15% | 4.1 | 86% |

Two effects:

- **Wrong labels shrink real differences.** An item with a wrong reference is scored wrong for both models, so it cannot show either one's improvement. With 15% wrong labels, a real 5-point gain measures as about 4.
- **They add to an uncertainty that was already there.** Even with perfect labels, a 300-item eval picks the better of two models only 91% of the time, because sampling noise is comparable to a 5-point difference. Wrong labels make that slightly worse. The larger lesson is the one from the evaluation science lab: **small eval sets cannot reliably separate similar models**, labels or no labels.

In this simulation the noise is mild because the wrong value is one no model gives. Label errors that agree with a common model mistake are worse: they reward the mistake. That happens with outdated facts, when the model learned the same old value the label holds.

## Auditing labels against the source

Most reference answers come from somewhere: a document, a policy, a database. The **label audit** checks each reference answer against the current version of the document for its fact, and flags any that the document does not support. In E2 it found every wrong label, with no false flags.

That works because the corpus is the source of truth here. Two cautions for real use:

- **The audit is only as good as the source.** If the knowledge source is stale, the audit will flag correct labels and approve stale ones. Run the corpus checks (article 06) first.
- **Not every label has a single source.** For open-ended answers, use two independent labellers and adjudication, as described in [Becoming an AI Quality Engineer](https://github.com/K11-Software-Solutions/becoming-ai-quality-engineer), and measure their agreement as the evaluation science lab describes.

## In CI

The gate fails if any reference answer disagrees with the current document for its fact. When a fact changes, the corpus and the eval set must change together, which is the point: a changed fact is a deliberate, reviewed change to both.

## Takeaways

- **Wrong labels shrink real differences and add noise.**
- **Most wrong labels are yesterday's right answers.** Re-check references when facts change.
- **Audit labels against their source, after checking the source.**
- **A 300-item eval set picks the better of two close models only about 9 times in 10, even with perfect labels.**
