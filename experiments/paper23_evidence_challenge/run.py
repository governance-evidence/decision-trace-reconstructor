"""Replay the frozen authored challenge without inference or changing V5."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

CHILD = r"""
import json, sys
from pathlib import Path
from reconstructor.core.manifest import FragmentManifest
from reconstructor.pipeline import reconstruct
from reconstructor.mapping.mapper import map_chain_to_schema_aggregate
cases=json.loads(Path(sys.argv[1]).read_text()); output=[]
for case in cases:
    data=dict(case['manifest'])
    if sys.argv[2]=='coverage':data.pop('evidence_contract',None)
    m=FragmentManifest.from_dict(data)
    kwargs={'evidence_contract':m.evidence_contract} if hasattr(m,'evidence_contract') else {}
    r=reconstruct(m.fragments,m.architecture,m.stack_tier,m.scenario_id,**kwargs)
    verdicts=map_chain_to_schema_aggregate(r.chain,m.architecture,m.stack_tier,**kwargs)
    output.append(dict(case_id=case['case_id'],per_property=[dict(property=v.property_name,category=v.category.value,gap=v.gap_description) for v in verdicts]))
print(json.dumps(output,sort_keys=True))
"""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text())


def verify(repo: Path, study: Path) -> None:
    freeze = read(study / "input-freeze.json")
    assert sha(study / "cases.json") == freeze["cases_sha256"]
    assert sha(study / "PROTOCOL.md") == freeze["protocol_sha256"]
    v5 = repo / "study-data/paper23-20261010-assessor-v5"
    current = {str(p.relative_to(v5)): sha(p) for p in sorted(v5.rglob("*")) if p.is_file()}
    assert current == freeze["v5_files"], "V5 files changed"
    for rel, digest in freeze["archives"].items():
        assert sha(repo / rel) == digest
    for rel, digest in freeze["source_files"].items():
        assert sha(study / "instrument-before" / rel) == digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    study = args.study.resolve()
    out = args.output.resolve()
    if out.exists():
        raise SystemExit("Preserve results: choose a new output directory")
    verify(repo, study)
    cases = read(study / "cases.json")
    assert len(cases) == 20 and sum(c["expected_full"] for c in cases) == 10
    out.mkdir(parents=True)
    code_paths = sorted((repo / "src").rglob("*.py")) + [
        Path(__file__),
        repo / "experiments/paper23/packets.py",
    ]
    code_freeze = {str(p.relative_to(repo)): sha(p) for p in code_paths}
    (out / "code-freeze.json").write_text(json.dumps(code_freeze, indent=2, sort_keys=True) + "\n")
    # Keep an executable source snapshot for each scored run, even if development continues.
    for path in code_paths:
        target = out / "instrument" / path.relative_to(repo)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    variants = {
        "pinned_v0_1_0": (
            repo / "study-data/paper23-20261010-assessor-v5/instrument-v0.1.0/src",
            "legacy",
        ),
        "pre_change_current": (study / "instrument-before/src", "legacy"),
        "revised_coverage": (out / "instrument/src", "coverage"),
        "revised_typed": (out / "instrument/src", "typed"),
    }
    predictions = {}
    for name, (source, mode) in variants.items():
        process = subprocess.run(
            [sys.executable, "-B", "-c", CHILD, str(study / "cases.json"), mode],
            cwd=out,
            capture_output=True,
            text=True,
            timeout=60,
            env={
                "PATH": os.environ.get("PATH", ""),
                "PYTHONPATH": str(source),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
        (out / f"{name}-process.json").write_text(
            json.dumps(
                dict(returncode=process.returncode, stdout=process.stdout, stderr=process.stderr),
                indent=2,
            )
            + "\n"
        )
        if process.returncode:
            raise RuntimeError(f"{name} failed; retained process output")
        predictions[name] = json.loads(process.stdout)
    sys.path.insert(0, str(repo))
    from experiments.paper23.packets import baseline

    results = []
    for c in cases:
        scores = {"baseline": baseline(c["packet"])[c["target"]]}
        gaps = {}
        for name, items in predictions.items():
            row = next(x for x in items if x["case_id"] == c["case_id"])
            p = next(p for p in row["per_property"] if p["property"] == c["target"])
            scores[name] = p["category"]
            gaps[name] = p["gap"]
        results.append(
            dict(
                case_id=c["case_id"],
                pair=c["pair"],
                target=c["target"],
                expected_full=c["expected_full"],
                predictions=scores,
                gaps=gaps,
                passed={
                    name: (value == "fully_fillable") == c["expected_full"]
                    for name, value in scores.items()
                },
            )
        )
    summary = {}
    for name in ["baseline", *variants]:
        tp = sum(r["expected_full"] and r["predictions"][name] == "fully_fillable" for r in results)
        fp = sum(
            not r["expected_full"] and r["predictions"][name] == "fully_fillable" for r in results
        )
        fn = 10 - tp
        tn = 10 - fp
        summary[name] = dict(
            correct=tp + tn,
            total=20,
            tp=tp,
            fp=fp,
            fn=fn,
            tn=tn,
            failures=[r["case_id"] for r in results if not r["passed"][name]],
        )
    verify(repo, study)
    assert {str(p.relative_to(repo)): sha(p) for p in code_paths} == code_freeze
    record = dict(
        schema="paper23-evidence-challenge-v1",
        reference="Authored pre-implementation development expectations; not independent validation",
        cases_sha256=sha(study / "cases.json"),
        code_freeze_sha256=sha(out / "code-freeze.json"),
        primary_endpoint="Prespecified target property, full versus non-full; other properties exploratory",
        summary=summary,
        results=results,
        all_property_predictions=predictions,
        v5_unchanged=True,
        archive_hashes_verified=read(study / "input-freeze.json")["archives"],
        inference_calls=0,
        inference_cost_usd=0,
    )
    (out / "results.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps(dict(output=str(out), summary=summary, v5_unchanged=True), indent=2))


if __name__ == "__main__":
    main()
