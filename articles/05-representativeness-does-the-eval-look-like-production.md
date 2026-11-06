# 05. Representativeness: Does the Eval Set Look Like Production?

> **Series:** AI Data Quality Lab · [Index](../README.md#articles) · Previous: [04](04-label-noise-when-the-answer-key-is-wrong.md) · Next: [06. RAG Corpus Health and Privacy](06-rag-corpus-health-and-privacy.md)

An eval set answers "how good is the model **on these questions**?". The question people actually ask is "how good is it **for our users**?". The two are the same only if the eval set looks like the traffic.

## How eval sets drift away from production

Eval sets are usually written by people, in one sitting, about the features they know best, in their own language. Easy topics are over-represented because they are easy to write questions for. Hard topics, non-English users and new features are under-represented, and those are often where the model is weakest.

## Experiment E3

The same model scored on two eval sets: one that matches the production mix of topics and languages, and one skewed towards easy topics and English:

| Eval set | Topic PSI | Language PSI | Measured accuracy | Reweighted to production | True production accuracy |
|---|---|---|---|---|---|
| matches production | 0.02 | 0.00 | 66.5% | 67.2% | 67.0% |
| skewed to easy topics and English | **1.15** | **1.57** | **79.0%** | 68.0% | 67.0% |

The skewed set reports the model **12 points better** than users experience. Nothing is wrong with any individual item: every question is correct, every reference answer is right. The problem is only what was left out.

## Measuring the mismatch

The **population stability index** (PSI) compares two distributions over the same categories (here, topics and languages):

```text
PSI = sum over categories of (eval share - production share) × ln(eval share / production share)
```

The usual reading: under 0.1, little difference; 0.1 to 0.25, a moderate shift; above 0.25, a large one. The skewed set's PSI is over 1 on both dimensions. The gate fails above 0.1.

It needs only a production **sample** with the attributes you care about (topic, language, customer segment, channel), which most teams already have in their logs. The [AI Production Monitoring Lab](https://github.com/K11-Software-Solutions/ai-production-monitoring-lab) uses the same statistic to watch production traffic itself drift over time.

## Correcting for it

If the eval set has enough items in every topic, **reweighting** recovers a good production estimate: compute accuracy per topic, then average with the production mix as weights. In E3 that brought the skewed set's 79% down to 68%, within a point of the truth.

Reweighting cannot fix topics the eval set barely covers: with three tax questions, the tax accuracy estimate is too noisy to weight heavily. The real fix is to **sample new eval items from production traffic**, stratified by topic and language, and label them.

## Takeaways

- **An eval score is about the eval set's questions, not about your users.**
- **Compare the eval mix with production on every attribute that changes difficulty**, and gate on PSI.
- **Reweight by the production mix to estimate production accuracy**, if every group has enough items.
- **Build eval sets by sampling production**, not only by writing questions.
