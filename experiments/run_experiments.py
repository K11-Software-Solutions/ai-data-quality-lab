"""Experiments behind the articles' findings.

    python -m experiments.run_experiments         # about a minute; writes experiments/results/

E1  Contamination: how much leaked eval items inflate accuracy, and what exact and
    near-duplicate checks catch (verbatim and reworded leaks).
E2  Label noise: how wrong reference answers shrink the measured gap between two models
    and how often the eval then picks the wrong one; what a label audit finds.
E3  Representativeness: an eval set skewed towards easy topics, against production; reweighting.
E4  RAG corpus health: stale and contradictory documents, with random and newest-first retrieval.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from dqlab import checks, sim
from dqlab.data import build

OUT = Path(__file__).parent / "results"


def mean(xs):
    return sum(xs) / len(xs)


def e1_contamination(model_seeds: int = 20) -> dict:
    clean = build()
    clean_mem = sim.memorised_ids(clean["eval"], clean["train"])
    clean_acc = mean([sim.score_model(clean["eval"], clean["train"], s, memorised=clean_mem)["accuracy"] for s in range(model_seeds)])
    rows = []
    for share in (0.05, 0.1, 0.2, 0.3):
        d = build("contaminated", leak_share=share)
        mem = sim.memorised_ids(d["eval"], d["train"])
        acc = mean([sim.score_model(d["eval"], d["train"], s, memorised=mem)["accuracy"] for s in range(model_seeds)])
        con = checks.contamination(d["eval"], d["train"])
        exact, flagged = set(con["exact"]), set(con["exact"]) | set(con["near"])
        lv, lr = set(d["meta"]["leaked_verbatim"]), set(d["meta"]["leaked_reworded"])
        kept = [r for r in d["eval"] if r["id"] not in flagged]
        acc_clean = mean([sim.score_model(kept, d["train"], s, memorised=mem)["accuracy"] for s in range(model_seeds)])
        rows.append({"leaked_share": share, "measured_accuracy": round(acc, 3), "inflation_points": round(100 * (acc - clean_acc), 1),
                     "exact_catches_verbatim": round(len(exact & lv) / len(lv), 2),
                     "exact_catches_reworded": round(len(exact & lr) / len(lr), 2),
                     "near_dup_catches_reworded": round(len(flagged & lr) / len(lr), 2),
                     "other_items_flagged": len(flagged - lv - lr),
                     "accuracy_after_removing_flagged": round(acc_clean, 3)})
    return {"clean_accuracy": round(clean_acc, 3), "production_accuracy": round(sim.production_accuracy(), 3),
            "model_seeds": model_seeds, "rows": rows}


def e2_label_noise(trials: int = 200) -> dict:
    rows = []
    for share in (0.0, 0.04, 0.08, 0.15):
        d = build("noisy-labels", noise_share=share) if share else build()
        mem = sim.memorised_ids(d["eval"], d["train"])
        right = gap = 0.0
        for t in range(trials):
            a = sim.score_model(d["eval"], d["train"], seed=2 * t, memorised=mem)["accuracy"]
            b = sim.score_model(d["eval"], d["train"], seed=2 * t + 1, skill_shift=0.05, memorised=mem)["accuracy"]
            right += b > a
            gap += b - a
        flagged = set(checks.label_audit(d["eval"], d["corpus"]))
        noisy = set(d["meta"]["noisy"])
        rows.append({"wrong_labels": share, "measured_gap_points": round(100 * gap / trials, 1),
                     "picks_better_model": round(right / trials, 2),
                     "audit_finds_wrong_labels": round(len(flagged & noisy) / len(noisy), 2) if noisy else "-",
                     "audit_false_flags": len(flagged - noisy)})
    return {"true_gap_points": 5.0, "trials": trials, "rows": rows}


def e3_representativeness(model_seeds: int = 20) -> dict:
    rows = []
    for label, variant in (("matches production", ""), ("skewed to easy topics and English", "skewed-eval")):
        d = build(variant)
        mem = sim.memorised_ids(d["eval"], d["train"])
        scores = [sim.score_model(d["eval"], d["train"], s, memorised=mem) for s in range(model_seeds)]
        per_topic = {t: mean([s["per_topic"].get(t, 0) for s in scores]) for t in scores[0]["per_topic"]}
        rep = checks.representativeness(d["eval"], d["production"])
        rows.append({"eval_set": label, "topic_psi": round(rep["topic_psi"], 3), "lang_psi": round(rep["lang_psi"], 3),
                     "measured_accuracy": round(mean([s["accuracy"] for s in scores]), 3),
                     "reweighted_to_production": round(sim.reweighted(per_topic), 3),
                     "production_accuracy": round(sim.production_accuracy(), 3)})
    return {"rows": rows}


def e4_rag() -> dict:
    rows = []
    for label, variant in (("clean", ""), ("5 stale documents", "stale-corpus"), ("4 contradicting documents", "contradictory")):
        corpus = build(variant)["corpus"]
        health = checks.corpus_health(corpus)
        cleaned = [d for d in corpus if d["id"] not in set(health["stale"])]
        rows.append({"corpus": label, "stale_found": len(health["stale"]), "contradictions_found": len(health["contradictions"]),
                     "accuracy_random_retrieval": round(sim.rag_accuracy(corpus), 3),
                     "accuracy_newest_first": round(sim.rag_accuracy(corpus, newest_first=True), 3),
                     "accuracy_after_removing_stale": round(sim.rag_accuracy(cleaned), 3)})
    return {"rows": rows}


def table(rows: list[dict]) -> list[str]:
    cols = list(rows[0])
    return ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] + \
           ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in rows]


def main() -> int:
    res = {"E1": e1_contamination(), "E2": e2_label_noise(), "E3": e3_representativeness(), "E4": e4_rag()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "experiments.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    e1 = res["E1"]
    L = ["# Experiment results", "", "Generated by `python -m experiments.run_experiments`. Deterministic: rerunning gives the same numbers.", "",
         f"## E1. Contamination (clean eval accuracy {e1['clean_accuracy']}, production accuracy {e1['production_accuracy']}; "
         f"{e1['model_seeds']} model seeds; leaks half verbatim, half reworded)", ""] + table(e1["rows"])
    L += ["", f"## E2. Wrong reference labels (model B truly {res['E2']['true_gap_points']:.0f} points better; {res['E2']['trials']} trials)", ""] + table(res["E2"]["rows"])
    L += ["", "## E3. Representativeness", ""] + table(res["E3"]["rows"])
    L += ["", "## E4. RAG corpus health (1,000 questions)", ""] + table(res["E4"]["rows"])
    (OUT / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
