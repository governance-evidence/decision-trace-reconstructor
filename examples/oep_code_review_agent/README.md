# OEP code-review-agent contract example

Vendored snapshot of the Operational Evidence Plane (OEP) generic-jsonl
integration, pinning the cross-repo contract exercised by OEP's
`make validate-dtr` target.

Provenance: copied from
[`operational-evidence-plane`](https://github.com/agent-runtime-evidence/operational-evidence-plane)
`integrations/decision-trace-reconstructor/` at OEP v0.3.1:

- `input/mapping.v0.yaml` — generic-jsonl mapping (schema_version 1.0)
- `input/code_review_agent.jsonl` — committed JSONL projection of the OEP
  code-review evidence chain
- `expected_output/feasibility.json` — copy of OEP's
  `code_review_agent.expected_feasibility.json`

`tests/integration/test_example_oep_code_review.py` replays the
ingest-and-reconstruct path over this snapshot so a breaking change to the
generic-jsonl mapping parser or the feasibility report shape fails in this
repository's CI, not only in OEP.

To refresh after an intentional contract change: re-copy the three files
from the OEP repository and update both repositories in the same change
window.
