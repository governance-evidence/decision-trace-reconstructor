# AI assessment and pinned DTR scoring

This implements the operator-requested amendment after the excluded calibration pilot. It is an exploratory AI-reference comparison, not independent human validation. The generator and assessor both use `openai/gpt-4.1-mini` on the fixed OpenAI provider route. Their errors can be correlated. The AI label is not factual ground truth.

Every assessment sees one packet and the fixed rubric in a fresh conversation, without its paired view, the hidden ledger or DTR/baseline predictions. Reduced assessments are frozen before full assessments. The validator checks schema and cited-record membership, not semantic correctness. A single correction attempt is allowed for malformed output or an invalid evidence ID; both responses remain recorded. All requests share the original study's USD 5 budget, including previous pilot failures and unknown-usage reservations.

The pinned DTR source is extracted from Git commit `40f72522664964e1a467e75420c4f792465b4046` into local study storage, hashed, and executed in a subprocess with that source directory ahead of the installed development package. It receives only the normalised packet. Six observable rows are primary; opaque reasoning is listed separately. Boundary metrics are omitted because no independent boundary reference exists.

## Commands

```sh
.venv/bin/python -m experiments.paper23_analysis freeze-analysis --study study-data/paper23-20261010
.venv/bin/python -m experiments.paper23_analysis judge --study study-data/paper23-20261010 --phase pilot --pass-name reduced --env-file /path/to/working/.env
.venv/bin/python -m experiments.paper23 freeze-labels --study study-data/paper23-20261010 --phase pilot --pass-name reduced
.venv/bin/python -m experiments.paper23_analysis judge --study study-data/paper23-20261010 --phase pilot --pass-name full --env-file /path/to/working/.env
.venv/bin/python -m experiments.paper23 freeze-labels --study study-data/paper23-20261010 --phase pilot --pass-name full
.venv/bin/python -m experiments.paper23 freeze --study study-data/paper23-20261010
```

Run the main matrix with the capture commands only after these steps and the pilot capture audit. Preserve actual user decisions at every human gate. After all main attempts, construct packets, repeat `judge` and `freeze-labels` with `--phase main` (reduced then full), then run:

```sh
.venv/bin/python -m experiments.paper23_analysis score --study study-data/paper23-20261010 --phase main
```

Frozen source and annotation hashes are checked before scoring. Scoring writes the adapted manifest, raw instrument output, process timing, row-level comparison, descriptive summaries and discrepancies. It refuses to overwrite an existing scoring directory. Processing failures remain in coverage and as failed predictions; empty denominators are null. Row and paired-view dependence prohibit treating 432 primary rows as independent trials. All counts and rates are relative to the AI reference and require qualified interpretation.

The protocol amendment and source-equivalence check are stored in the study's `revisions/ai-assessment-amendment.json`. No generator, sandbox, task prompt, adapter mapping or deletion logic changed as part of switching annotation attribution. Study data remain local; no deposit or publication is performed by these commands.
