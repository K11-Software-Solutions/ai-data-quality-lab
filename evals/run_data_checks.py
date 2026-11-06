"""Data-quality gate: run every check on the datasets and fail on any finding.

Usage (from the repo root):

    python -m evals.run_data_checks                          # the committed data in data/
    DATA_VARIANT=contaminated python -m evals.run_data_checks   # a dataset with a known problem: must FAIL
    python -m evals.run_data_checks --update-manifest        # accept the current data as the new version

The manifest (data/manifest.json) pins a content fingerprint for every dataset. Changing a
dataset without updating the manifest fails the gate, so data changes are always deliberate
and reviewable, like code changes.

Writes evals/results/data_report.md and .json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dqlab import checks
from dqlab.data import DATA, build, load

HERE = Path(__file__).parent
MANIFEST = DATA / "manifest.json"


def run(datasets: dict, thresholds: dict) -> tuple[dict, list[str]]:
    ev, train, corpus, prod = datasets["eval"], datasets["train"], datasets["corpus"], datasets["production"]
    texts = {**{d["id"]: d["text"] for d in corpus}, **{r["id"]: r.get("question", "") for r in ev},
             **{t["id"]: t["question"] for t in train}}
    con = checks.contamination(ev, train, threshold=thresholds["near_duplicate_threshold"])
    health = checks.corpus_health(corpus)
    rep = checks.representativeness(ev, prod)
    findings = {
        "contamination_exact": con["exact"], "contamination_near": con["near"],
        "eval_duplicates": checks.duplicates(ev), "schema": checks.schema(ev),
        "label_audit": checks.label_audit(ev, corpus) if not checks.schema(ev) else [],
        "pii": checks.pii(texts), "stale_documents": health["stale"], "contradictions": health["contradictions"],
    }
    metrics = {"coverage": checks.coverage(corpus, prod), "topic_psi": rep["topic_psi"], "lang_psi": rep["lang_psi"],
               "fingerprints": {k: checks.fingerprint(v) for k, v in datasets.items() if k != "meta"}}
    failures = [f"{name}: {len(items)} finding(s), e.g. {items[:3]}" for name, items in findings.items() if items]
    if metrics["coverage"] < thresholds["min_coverage"]:
        failures.append(f"coverage: {metrics['coverage']:.2f} < {thresholds['min_coverage']}")
    for k in ("topic_psi", "lang_psi"):
        if metrics[k] > thresholds["max_psi"]:
            failures.append(f"representativeness: {k} = {metrics[k]:.3f} > {thresholds['max_psi']}")
    return {"findings": findings, "metrics": metrics}, failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-gate", action="store_true")
    parser.add_argument("--update-manifest", action="store_true")
    parser.add_argument("--out", type=Path, default=HERE / "results")
    args = parser.parse_args(argv)
    variant = os.environ.get("DATA_VARIANT", "")
    datasets = build(variant) if variant else load()
    thresholds = json.loads((HERE / "thresholds.json").read_text(encoding="utf-8"))
    result, failures = run(datasets, thresholds)
    prints = result["metrics"]["fingerprints"]
    if args.update_manifest:
        MANIFEST.write_text(json.dumps(prints, indent=2) + "\n", encoding="utf-8")
    pinned = json.loads(MANIFEST.read_text(encoding="utf-8"))
    changed = [k for k in pinned if pinned[k] != prints.get(k)]
    if changed:
        failures.append(f"manifest: {', '.join(changed)} changed without updating data/manifest.json")

    m = result["metrics"]
    L = [f"# Data quality report{f': variant `{variant}`' if variant else ''}", "",
         "| Check | Findings |", "|---|---|"]
    L += [f"| {name} | {len(items)} |" for name, items in result["findings"].items()]
    L += [f"| coverage of production topics | {m['coverage']:.2f} (min {thresholds['min_coverage']}) |",
          f"| eval vs production, topic PSI | {m['topic_psi']:.3f} (max {thresholds['max_psi']}) |",
          f"| eval vs production, language PSI | {m['lang_psi']:.3f} (max {thresholds['max_psi']}) |",
          "", "Fingerprints: " + ", ".join(f"`{k}@{v}`" for k, v in prints.items()) + (f"  (changed: {', '.join(changed)})" if changed else ""),
          "", "## Gate", "", "PASSED" if not failures else "FAILED:\n" + "\n".join(f"- {f}" for f in failures), ""]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "data_report.md").write_text("\n".join(L), encoding="utf-8")
    (args.out / "data_report.json").write_text(json.dumps({"variant": variant, **result, "gate_failures": failures},
                                                         indent=2), encoding="utf-8")
    print("\n".join(L))
    if failures and not args.no_gate:
        print("Data quality gate FAILED", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
