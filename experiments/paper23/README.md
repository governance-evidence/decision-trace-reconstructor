# Paper23 controlled real-model evaluation

Current annotation mode (operator amendment, 2026-10-10): `ai_assessed`. The operator requested AI annotation after the six-cell pilot completed. The author-form workflow below is preserved as the original option; current execution follows [the AI assessment and scoring workflow](../paper23_analysis/README.md). No human sufficiency labels or human annotation times are claimed. Actual execution approvals remain human responses.

This is a separate capture harness, not a change to the DTR instrument or its synthetic benchmark. The scientific protocol is copied into each local study before execution. The primary DTR instrument remains commit `40f72522664964e1a467e75420c4f792465b4046` (v0.1.0); the current development package must not replace it during scoring.

The operator authorised implementation and execution on 2026-10-10, including at most USD 5 aggregate OpenRouter inference charges across the excluded pilot, main attempts and retries. Use an existing local `OPENROUTER_API_KEY` environment variable or pass only an existing credential file path with `--env-file`. The file reader reads that single assignment without sourcing shell code. Secrets are neither printed nor copied into study records.

## Commands

From the DTR repository with its development environment:

```sh
make test PYTHON=.venv/bin/python
make paper23-study PYTHON=.venv/bin/python ARGS='init --study study-data/paper23-20261010 --protocol /absolute/path/to/protocol.md'
make paper23-study PYTHON=.venv/bin/python ARGS='probe --study study-data/paper23-20261010 --env-file /absolute/path/to/.env'
make paper23-study PYTHON=.venv/bin/python ARGS='run --study study-data/paper23-20261010 --phase pilot --env-file /absolute/path/to/.env'
make paper23-study PYTHON=.venv/bin/python ARGS='status --study study-data/paper23-20261010'
```

`probe` checks credential validity and the current fixed model listing without generating model output. `run` executes scheduled attempts sequentially. Four pilot cells are autonomous; two pause on concrete calendar proposals in `runs/<run-id>/human-request.json`. Only after the operator answers that actual proposal may `decide --run-id ... --decision approve|deny --evidence 'actual human response and provenance'` be called. Calling `run` again resumes pending tools without repeating a completed run. A process interrupted during a model call remains `calling_model`: preserve its transport records and reconcile it explicitly instead of silently replaying.

Use `packets --phase pilot` to build the twelve pilot packets and two blank annotation forms for the prespecified timing sample (the full and authority-reduced views of `pilot-05`). The author completes the reduced form first, entering actual times, answers, evidence IDs, reasons and labels, and sets `origin` to `author_entered`. Freeze that pass with `freeze-labels --phase pilot --pass-name reduced`; only then complete and freeze the full pass. The two-packet calibration estimates annotation effort approximately; it does not measure all architecture-specific burdens. No AI-generated sufficiency labels are substituted for author input.

After pilot checks and annotation calibration, `freeze` preserves protocol/source hashes, pilot label hashes and cost. `run --phase main` refuses to start without that freeze. A change after pilot initiation is an explicitly documented new pilot revision, never a silent continuation. The main annotation forms cover all 72 packets, reduced before full. DTR and baseline predictions must stay hidden until labels are frozen. Final scoring and manuscript integration remain subsequent work; this runner makes no scientific-readiness claim.

If a pilot exposes an infrastructure or harness defect, `revise-pilot --evidence 'specific defect and correction'` preserves the previous configuration and attempts, creates new `pilot-rN-*` IDs and retains the same aggregate budget ledger. It is forbidden after the main freeze. The annotation timing sample remains the human within-stack cell ending in `-05`. The first live pilot exposed an unsupported `parallel_tool_calls` parameter under strict provider routing; revision 2 removes that optional parameter. Multiple calls in one response, if returned, are executed sequentially under the same tool-invocation cap. Unresolved failed-request reservations remain counted in the USD 5 cap and are disclosed separately from reported charges; they are not treated as free or required to become an invented exact bill before protocol freeze.

## Evidence boundary and adapter

The evaluated packet consists of `application-events.jsonl` and `service-events.jsonl`. Transport requests and responses are preserved separately in `transport/` for provenance, usage and reproducibility; they are not part of any evaluated packet. They contain repeated conversation history, which would otherwise leak deleted receipts. The authoritative state ledger and factual checks are separate from the adapter. Packet JSON contains no planned reference verdicts.

`A` removes entire `authority` and `human_decision` records and duplicated `data.reason=human_denied` fields in tool/service results. Actor IDs, business policy, operational tool configuration and model narratives remain. `O` removes `final_state_check` records and all tool/service result copies except pre-decision `inspect_state` reads (`status=read, phase=before`). Requested calls and model narratives remain. Each manifest lists exact removed IDs/fields; missing removal targets are visible through an empty list and are not invented.

`adapt(packet)` accepts only the packet value. Configuration maps to `config_snapshot`, policy to `policy_snapshot`, delegation to `agent_message`, prompts and pre-decision reads to `retrieval_result`, model messages to `model_generation`, requests to `tool_call`, human decisions to their corresponding human fragment kind, and execution/read-back observations to `state_mutation`. A refusal or unchanged final state is an observation represented by that last type; it does not assert that a mutation occurred. Payloads retain that distinction. Original IDs, numeric timestamps, actors, external causal IDs and payloads are preserved. The packet ID is a decision-group hint because each scenario defines one target business decision; extra actions remain in that group and are not discarded. No missing parent is fabricated or resolved from hidden records.

The simple baseline requires nonempty delegation identity/scope for actor-authority, a prompt for inputs, version/text for policy, tools/resource scope for configuration, a tool request for output action, and an executor receipt plus final-state record for outcome. It does not check consistency, causality or whether all sub-obligations were satisfied. These intentionally weak rules are frozen with the adapter.

## Measurement limits

The six main cards are controlled fictitious tasks, each run once per architecture/topology. Cross-stack uses a separate Python process with separate durable service state and logs; both process IDs are recorded. It models a process boundary, not a remote enterprise deployment. Policy enforcement in the sandbox is intentional, so task success is not a general model-safety score.

The state verifier independently reads the committed state and tests postconditions without invoking the synthetic generator or DTR. It shares case definitions with the executor; its factual assertions are not an independent human assessment. For refusal cases an unchanged state alone is insufficient for task completion: report `terminal_recorded` and execution status alongside `state_matches_expected`. Model errors, extra actions and failed attempts remain in the ledger.

The budget reserves a conservative UTF-8 payload-byte input bound plus framing allowance and the output cap at the fixed maximum rates before each request. Uncertain requests retain their reservation; every retry counts against aggregate and per-trajectory limits. Any observed charge above its reservation permanently halts new calls for reconciliation. This bounds intended charges under the provider's advertised rate contract; it is not a billing guarantee against provider errors. Human wait, API latency, local processing and downstream scoring must be reported separately. Study data are local and Git-ignored until an explicit publication/deposit decision.
