# AI Data Quality Lab

[![CI quality gates](https://github.com/K11-Software-Solutions/ai-data-quality-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/K11-Software-Solutions/ai-data-quality-lab/actions/workflows/ci.yml)
[![Code: MIT](https://img.shields.io/badge/Code-MIT-blue.svg)](LICENSE) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24025319.svg)](https://doi.org/10.5281/zenodo.24025319) [![Articles: CC BY 4.0](https://img.shields.io/badge/Articles-CC%20BY%204.0-lightgrey.svg)](articles/LICENSE.md)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![No dependencies](https://img.shields.io/badge/runtime%20deps-none-success)
![No API key needed](https://img.shields.io/badge/API%20key-not%20required-success)

**Test the data behind an AI system like code: eval contamination, wrong reference labels, unrepresentative eval sets, stale and contradictory RAG documents, personal data, broken rows and unreviewed data changes, each gated in CI and proven with data that must fail.**

The eighth lab in a series for quality engineers moving into AI:

| Lab | Question it answers |
|---|---|
| [Becoming an AI Quality Engineer](https://github.com/K11-Software-Solutions/becoming-ai-quality-engineer) | Is the RAG **application** good enough to ship? |
| [LLM Model Testing Lab](https://github.com/K11-Software-Solutions/llm-model-testing-lab) | Is the **model** good enough? |
| [Agent Testing Lab](https://github.com/K11-Software-Solutions/agent-testing-lab) | Is the **agent** safe to let act? |
| [AI Production Monitoring Lab](https://github.com/K11-Software-Solutions/ai-production-monitoring-lab) | Is it **still** good, for the users we actually have, right now? |
| [Multi-Agent Testing Lab](https://github.com/K11-Software-Solutions/multi-agent-testing-lab) | When **agents work together**, does the team do the right thing, and who broke it when it doesn't? |
| [AI Performance and Cost Lab](https://github.com/K11-Software-Solutions/ai-performance-cost-lab) | Is it **fast enough under load**, and what does each **good answer** cost? |
| [AI Evaluation Science Lab](https://github.com/K11-Software-Solutions/ai-evaluation-science-lab) | Can we **trust the evaluator**, and how sure are we? |
| **AI Data Quality Lab** (this repo) | Is the **data** behind it all fit to learn from, test with and retrieve? |

## How it works

Four datasets for a fictional accounting app, LedgerLite, generated deterministically and committed to [`data/`](data): fine-tuning examples from support tickets, a 300-item eval set, a RAG corpus with dated documents, and a sample of production traffic. One command injects a known problem at a known size, with the ground truth recorded, so every check can be measured: what it finds, what it misses, and what the problem does to accuracy, model comparisons, production estimates and RAG answers.

## Articles

| # | Article |
|---|---|
| 01 | [Why Data Quality Decides AI Quality](articles/01-why-data-quality-decides-ai-quality.md) |
| 02 | [Four Datasets and What Hides in Them](articles/02-four-datasets-and-what-hides-in-them.md) |
| 03 | [Contamination: When the Test Is in the Training Data](articles/03-contamination-when-the-test-is-in-the-training-data.md) |
| 04 | [Label Noise: When the Answer Key Is Wrong](articles/04-label-noise-when-the-answer-key-is-wrong.md) |
| 05 | [Representativeness: Does the Eval Set Look Like Production?](articles/05-representativeness-does-the-eval-look-like-production.md) |
| 06 | [RAG Corpus Health and Privacy](articles/06-rag-corpus-health-and-privacy.md) |
| 07 | [Data Contracts and Versioning](articles/07-data-contracts-and-versioning.md) |
| 08 | [CI Gates, Negative Controls and Limitations](articles/08-ci-gates-negative-controls-limitations.md) |

## Quick start

Requirements: Python 3.11+. No runtime dependencies and no API key.

```bash
git clone https://github.com/K11-Software-Solutions/ai-data-quality-lab.git
cd ai-data-quality-lab
python -m venv .venv
source .venv/bin/activate              # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

```bash
pytest                                                       # 29 tests
python -m evals.run_data_checks                              # every check on the committed data
DATA_VARIANT=contaminated python -m evals.run_data_checks    # a dataset with a known problem: must fail
python -m experiments.run_experiments                        # the four experiments behind the articles
```

## Repository layout

```text
dqlab/
  data.py      the LedgerLite fact table, templates and generator; eight injectable problems with ground truth
  checks.py    contamination (exact, near-duplicate), duplicates, schema, label audit, PII (with Luhn),
               stale and contradictory documents, coverage, representativeness (PSI), fingerprints
  sim.py       a model with memorisation and per-topic skill; production accuracy and reweighting; RAG answers
data/          train, eval, corpus and production samples (JSON Lines) and manifest.json with pinned fingerprints
evals/
  run_data_checks.py   the data-quality gate
  thresholds.json      near-duplicate threshold, coverage and representativeness tolerances
experiments/   E1 contamination, E2 wrong labels, E3 representativeness, E4 RAG corpus; results committed
tests/         29 tests, including "committed data matches its generator"
articles/      the eight articles
.github/workflows/ci.yml   tests -> data gate + 8 broken datasets that must fail -> experiments reproducibility check
```

## What the lab finds

- **Contamination raises scores, so it never looks like a bug.** Leaking 10% of the eval set into training made the model look 5 points better; 30% made it look nearly 10 points better.
- **Exact matching caught every copied question and only 13 to 29% of reworded ones;** word-overlap similarity caught about 60%. Removing everything flagged still left the score up to 3.7 points too high.
- **Leaking one question contaminates its near-twins**, which the model also answers from memory.
- **A 300-item eval set picked the better of two models 5 points apart only 91% of the time with perfect labels**, and wrong labels shrank the measured gap further. An audit against the source documents found every wrong label.
- **An eval set skewed to easy topics and English reported 79% accuracy where users got 67%;** reweighting to the production mix gave 68%.
- **Five stale documents cut RAG accuracy to 84%;** newest-first retrieval restored it, but nothing automatic fixed contradicting documents (86%).

## CI quality gates

Every push runs three jobs: **tests**; the **data-quality gate** on the committed data, plus eight broken datasets that must each fail for the right reason; and an **experiments** job that fails if the results differ from the committed ones.

## Limitations

Synthetic templated data, word-overlap contamination checks, a clean source of truth for the label audit, structured corpus metadata, pattern-based PII detection with a known false positive, and topic labels assumed on production traffic. [Article 08](articles/08-ci-gates-negative-controls-limitations.md#limitations) covers each.

## About

Created by **Kavita Jadhav**, founder of [K11 Software Solutions](https://github.com/K11-Software-Solutions), Senior SDET and AI Quality Engineer working on LLM evaluation, red teaming and agentic QA systems.

**Licences:** code under the [MIT License](LICENSE); the written material in [`articles/`](articles/LICENSE.md) under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (share and adapt with credit).

LedgerLite, its facts, its users and all data in this repository are fictional and synthetic. The personal data used in the `pii-leak` variant is made up and uses reserved example domains and test numbers.

## Citing

Use GitHub's **Cite this repository** button (from [`CITATION.cff`](CITATION.cff)). Each tagged release is archived on Zenodo with its own DOI. Cite the version you used:

> Jadhav, K. (2026). *AI Data Quality Lab* (Version v1.0.0) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.24025320

To refer to the project as a whole (always resolves to the latest version), use the concept DOI: https://doi.org/10.5281/zenodo.24025319
