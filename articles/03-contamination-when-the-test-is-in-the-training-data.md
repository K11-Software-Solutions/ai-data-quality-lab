# 03. Contamination: When the Test Is in the Training Data

> **Series:** AI Data Quality Lab · [Index](../README.md#articles) · Previous: [02](02-four-datasets-and-what-hides-in-them.md) · Next: [04. Label Noise](04-label-noise-when-the-answer-key-is-wrong.md)

An eval set measures how a model handles questions it has **not** seen. If eval questions end up in the training data (copied into a fine-tuning set, scraped from a public benchmark, pasted into a support macro that later became training data), the model can answer them from memory, and the eval measures memory instead of skill. The score goes **up**, which is why nobody goes looking.

## How much it inflates scores

Experiment E1 leaks a share of the 300 eval questions into the training data, half verbatim and half lightly reworded, and scores the model 20 times:

| Eval items leaked | Measured accuracy | Inflation |
|---|---|---|
| 0% | 66.5% | |
| 5% | 69.2% | +2.7 points |
| 10% | 71.5% | +5.0 points |
| 20% | 73.5% | +7.0 points |
| 30% | 76.1% | +9.6 points |

The real production accuracy is 67%. A 10% leak makes the model look 5 points better than it is: easily the size of the improvement a team is trying to measure.

## What the checks catch

Two checks compare every eval question with the training data:

- **Exact**: identical after normalising case, punctuation and ticket numbers.
- **Near-duplicate**: overlap of three-word sequences (word-trigram Jaccard similarity) of 0.5 or more.

| Eval items leaked | Exact catches verbatim leaks | Exact catches reworded leaks | Near-duplicate catches reworded leaks | Other items flagged |
|---|---|---|---|---|
| 5% | 100% | 29% | 57% | 27 |
| 10% | 100% | 20% | 60% | 49 |
| 20% | 100% | 13% | 57% | 65 |
| 30% | 100% | 13% | 64% | 79 |

**Exact matching is necessary and nowhere near sufficient.** It catches every verbatim copy and almost none of the reworded ones. Near-duplicate matching catches about 60% of reworded leaks. The rest are reworded enough that word overlap falls below the threshold: "What is the number of invoices on the Starter plan for my bakery?" against "Tell me count of invoices on Starter plan for my bakery?" has an overlap of only 0.25, which the test suite keeps as a documented miss.

**The "other items flagged" are not false alarms.** They are eval questions that were not leaked themselves but are near-copies of ones that were: the same template and fact with a different context phrase. The model answers them from memory too. Leaking one question contaminates its near-twins, which is why contamination is better measured by **similarity** than by identity.

## Removing what was found does not fully fix it

After dropping every flagged item, measured accuracy is still 1 to 3.7 points above the clean baseline (more at higher leak rates): the reworded leaks the checks missed are still inflating it. Decontamination by text overlap is partial. For a stronger check:

- compare **meaning**, not words: embedding similarity between eval and training items, with a threshold tuned on known paraphrases;
- **keep eval sets private**, and add a canary string to them so their appearance in any training data can be detected (the model-testing lab's planted canary works the same way);
- **compare performance on old and new eval items**: if a model does much better on items that have been public for a while, suspect contamination.

## In CI

The gate fails if any eval item is found in the training data, exactly or nearly. On the committed data both counts are zero; the `contaminated` variant must fail.

## Takeaways

- **Contamination raises scores, so it never looks like a bug.**
- **Exact matching catches copies; reworded leaks need similarity checks.**
- **Leaking one question contaminates its near-twins.**
- **Text-overlap checks are a floor, not a guarantee. Check meaning, and keep eval sets private.**
