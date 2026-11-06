# 07. Data Contracts and Versioning

> **Series:** AI Data Quality Lab · [Index](../README.md#articles) · Previous: [06](06-rag-corpus-health-and-privacy.md) · Next: [08. CI Gates, Negative Controls and Limitations](08-ci-gates-negative-controls-limitations.md)

The checks so far find problems in the content of data. Two simpler disciplines prevent many of them: a **contract** for what a valid row looks like, and **versioning** so that every result can be tied to the exact data it came from.

## The contract

Every eval row must have:

| Field | Rule |
|---|---|
| `id` | present, unique |
| `question`, `answer` | non-empty text |
| `fact` | the key of the fact being tested (what makes the label audit possible) |
| `topic` | one of the known topics (what makes representativeness and reweighting possible) |
| `lang` | the language code |

Plus no duplicate questions. These look trivial, and they are the checks that catch a broken export, a merge that duplicated half the set, or a row someone added by hand without a topic. The `schema-break` variant (a missing answer, an unknown topic, a duplicate ID) and the `duplicate-eval` variant (thirty repeated questions) must both fail the gate.

Duplicates matter more than they look: thirty repeated questions out of 300 give those questions double weight in every score, and if the model happens to be good or bad at them, the score moves for no reason.

## Fingerprints and the manifest

Every dataset gets a **fingerprint**: a hash of its content (the order of fields within a row does not matter; the order of rows does). [`data/manifest.json`](../data/manifest.json) pins the fingerprint of each committed file:

```json
{"train": "6e979b06a1d2", "eval": "b139515e7e38", "corpus": "5c5a0149c1ee", "production": "da981a597a9a"}
```

The gate recomputes them on every run. If a dataset changed and the manifest did not, the build fails. Changing data is then always a deliberate act: regenerate or edit the data, run `python -m evals.run_data_checks --update-manifest`, and commit both, where a reviewer can see that the data changed and why.

Fingerprints also go in every report, so a score can always be traced to the exact data behind it. Two scores computed on different data are not comparable, however similar the numbers look. The same idea runs through [Becoming an AI Quality Engineer](https://github.com/K11-Software-Solutions/becoming-ai-quality-engineer), where eval reports carry data fingerprints and CI keeps label changes and grader changes in separate commits.

## Generated data must match its generator

The lab's data files are generated, so one more test applies: the committed files must equal what the generator produces. If someone edits a data file by hand, or changes the generator without regenerating, the test fails. For hand-curated data the equivalent is a **changelog**: every change to an eval set recorded with a reason, as the rubric changelog does in repo 1.

## Takeaways

- **Write the contract down and check every row against it.** It catches the boring failures that cause the most damage.
- **Duplicates silently re-weight a score.**
- **Pin a fingerprint for every dataset and fail the build on unreviewed changes.**
- **Put fingerprints in every report.** A score without its data version is not comparable to anything.
