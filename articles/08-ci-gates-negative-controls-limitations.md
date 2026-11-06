# 08. CI Gates, Negative Controls and Limitations

> **Series:** AI Data Quality Lab · [Index](../README.md#articles) · Previous: [07](07-data-contracts-and-versioning.md)

## The gate

`python -m evals.run_data_checks` runs every check on the committed datasets and fails on any finding:

| Check | Fails when |
|---|---|
| contamination | any eval item is in the training data, exactly or as a near-duplicate (similarity ≥ 0.5) |
| eval duplicates | any question appears twice |
| schema | any row breaks the contract |
| label audit | any reference answer disagrees with the current document for its fact |
| PII | any email, phone number or Luhn-valid card number in any dataset |
| stale documents | any document is older than the newest one for its fact |
| contradictions | the newest documents for a fact disagree |
| coverage | under 95% of production questions have a document for their topic |
| representativeness | topic or language PSI between eval and production above 0.1 |
| manifest | a dataset changed without updating its pinned fingerprint |

Most of these have **zero tolerance**. That is deliberate: these are not statistics with noise, they are defects. One leaked eval item or one card number is a finding to fix, not a rate to keep under a threshold.

## Negative controls

CI rebuilds the data with each injected problem and requires the gate to fail, for the right reason:

| Variant | Must fail on |
|---|---|
| `contaminated` | contamination |
| `noisy-labels` | label audit |
| `skewed-eval` | representativeness |
| `stale-corpus` | stale documents |
| `contradictory` | contradictions |
| `pii-leak` | PII |
| `schema-break` | schema |
| `duplicate-eval` | eval duplicates |

The tests check the **reason**, not just the failure: a gate that rejected every bad dataset because the manifest changed would pass a naive negative control while checking nothing else.

## Reproducible experiments

The four experiments behind articles 03 to 06 are deterministic, and CI fails if their results differ from the committed [`experiments/results/summary.md`](../experiments/results/summary.md).

## Limitations

- **Synthetic, templated data.** Fifteen facts and a handful of templates. Real data is messier: free text, many languages, facts that are not one sentence. The checks' structure carries over; their thresholds need tuning on your data.
- **Word overlap, not meaning.** The contamination check misses about 40% of reworded leaks. Add embedding-based similarity for real use.
- **A clean source of truth.** The label audit assumes the corpus is right. In practice, run corpus checks first and route disagreements to a person.
- **Structured corpus metadata.** Staleness and contradiction checks rely on a fact key and a date per document. Unstructured corpora need claim extraction, which has its own error rate.
- **Pattern-based PII.** It has known false positives (long order numbers that look like phones) and will miss names, addresses and anything not in a fixed format.
- **Topic labels on production traffic.** Representativeness needs production questions labelled with the same attributes as the eval set; that labelling is itself a data-quality task.

## The series so far, and what is next

Data is the layer under every other lab in this series: the application's eval set, the model's benchmark, the agent's scenarios, production's feedback loop, the multi-agent lab's handoffs, the performance lab's workload and the evaluation science lab's labels. The planned final lab in the series gathers the evidence all of them produce into one **assurance case**: a single, reviewable argument that a system is fit to release.

## Takeaways

- **Treat data defects as defects: zero tolerance, fix at the source.**
- **Prove each check with a dataset that must fail, and check the reason.**
- **Know what your checks cannot see**, and say so in the report.
