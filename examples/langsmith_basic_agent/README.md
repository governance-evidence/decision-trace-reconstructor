# Worked example: LangSmith → Decision Trace Reconstructor (`langsmith_basic_agent`)

This example runs the **first executable trace adapter**: translation of a LangSmith / LangGraph trace into the fragments manifest and full property-level reconstruction. End-to-end, no network required.

## What the trace represents

A single-agent LangGraph deployment performs a routine knowledge-base admin task: *"archive the legacy product docs and confirm cleanup"*. The agent runs RAG retrieval, plans the action via Claude, hits an explicit **human-approval gate**, and executes the destructive `kb_archive` tool on operator approval.

Architecturally this is **human-in-the-loop, within-stack** — the agent runs entirely inside a governed LangGraph runtime with LangSmith checkpointing; no cross-stack tool boundaries.

The 8 LangSmith runs in `input/runs.json`:

| # | run_type | name | role |
|---|---|---|---|
| 1 | chain | `boot_config` | tagged `config_snapshot` (operator-supplied) |
| 2 | chain | `policy_check` | tagged `policy_snapshot` (operator-supplied) |
| 3 | chain | `user_query` | router node |
| 4 | retriever | `kb_search` | RAG retrieval |
| 5 | llm | `ChatAnthropic` | planner LLM |
| 6 | parser | `OutputParser` | **skipped by adapter** (internal LangChain transform) |
| 7 | chain | `human_approval_gate` | metadata `langgraph_node: human_approval` |
| 8 | tool | `kb_archive` | destructive (matches `--state-mutation-tools` regex) |

## Files

```
examples/langsmith_basic_agent/
├── README.md                   ← you are here
├── input/
│   └── runs.json               ← LangSmith trace export (offline replay)
└── expected_output/
    ├── fragments.json          ← what the adapter produces
    ├── feasibility.json        ← per-property reconstructability tensor
    └── trace.jsonld            ← W3C PROV-O graph
```

## Running it

Two-step pipeline. **No LangSmith API key needed** — the offline path uses `input/runs.json` directly:

```bash
# Step 1: ingest LangSmith trace -> fragments manifest
decision-trace ingest langsmith \
  --from-file examples/langsmith_basic_agent/input/runs.json \
  --scenario-id langsmith_basic_agent_demo \
  --architecture human_in_the_loop \
  --stack-tier within_stack \
  --state-mutation-tools "(archive|drop|delete|exec|push|publish)" \
  --out fragments.json

# Step 2: run the six-stage pipeline
decision-trace reconstruct fragments.json --out out/ --jsonld

# Step 3: verify bit-identical reproduction against the reference
diff -ru examples/langsmith_basic_agent/expected_output out
```

## What the adapter produces (8 runs → 8 fragments)

The 8 LangSmith runs map onto the following fragment kinds:

| LangSmith run | Adapter rule | Fragment kind |
|---|---|---|
| `boot_config` (tag: `config_snapshot`) | tag-driven (operator opt-in) | `config_snapshot` |
| `policy_check` (tag: `policy_snapshot`) | tag-driven (operator opt-in) | `policy_snapshot` |
| `user_query` (chain) | run_type → catch-all | `agent_message` |
| `kb_search` (retriever) | run_type → retriever | `retrieval_result` |
| `ChatAnthropic` (llm) | run_type → llm | `model_generation` (with `internal_reasoning: opaque`) |
| `OutputParser` (parser) | skipped via `skip_run_types=("parser","embedding")` | — |
| `human_approval_gate` (chain, metadata `langgraph_node: human_approval`) | metadata pattern match | `human_approval` (with `stack_tier: human`) |
| `kb_archive` (tool, name matches state-mutation regex) | tool + heuristic | `tool_call` + paired `state_mutation` |

The adapter elevates `human_approval_gate` to `stack_tier: human` automatically — it's the canonical signal that an operator was in the loop and the responsibility-ambiguity axis is testable on this trace.

## What the reconstructor reconstructs from those 8 fragments

| Metric | Value |
|---|---|
| Decision units detected | 5 |
| Reconstruction completeness | **94.3%** |
| Dominant operational mode | none (no structurally-unfillable property) |
| Dominant structural break | none |

Per-property feasibility:

| Property | Category | Notes |
|---|---|---|
| inputs | `fully_fillable` | retriever + agent_message both present |
| policy_basis | `fully_fillable` | operator-supplied policy_snapshot |
| operator_identity | `partially_fillable` | shared authorship agent + operator (HITL mode 7) |
| authorization_envelope | `fully_fillable` | operator-supplied config_snapshot |
| reasoning_trace | `opaque` | substituted by authorization envelope (by design) |
| output_action | `fully_fillable` | tool_call documented |
| post_condition_state | `fully_fillable` | state_mutation emitted by heuristic |

This is a "well-instrumented" outcome: the only non-trivial gap is the shared agent / operator authorship (which is exactly what the human-in-the-loop architecture trades off against). Any auditor reading this LangSmith trace via the reconstructor can reconstruct **6 of 7 properties at the fully_fillable level** plus 1 partial — sufficient for the §6.3 design checklist's "Step 1 audit" question.

## What this example demonstrates

1. **The operator-supplied evidence regime matters more than the runtime.** The LangSmith trace itself is identical regardless of whether the operator tags `policy_check` and `boot_config` — the reconstructor measures what gets recorded, not what the runtime nominally supports. With the tags, policy_basis and authorization_envelope are fully fillable; without them they would be structurally unfillable.

2. **State-mutation detection is a heuristic, not a guarantee.** The `--state-mutation-tools` regex is an operator-supplied opt-in. If you know your destructive tool names, set the regex; if not, the property defaults to `partially_fillable` (or worse) — which is the correct under-claim.

3. **Internal LangChain machinery is filtered out.** `OutputParser` (run_type `parser`) is skipped by default because it carries no governance signal. The same is true for `embedding`. The adapter is conservative: 8 input runs produce 8 fragments because one is dropped and one (`kb_archive`) emits two paired fragments.

## Network mode (when you have a real LangSmith key)

```bash
export LANGSMITH_API_KEY=...
decision-trace ingest langsmith \
  --trace-id <uuid-of-your-real-trace> \
  --scenario-id production_kb_archive_2025_04_15 \
  --architecture human_in_the_loop \
  --stack-tier within_stack \
  --state-mutation-tools "(archive|drop|delete|exec|push|publish)" \
  --out fragments.json
```

The output is identical in shape to the offline path — the only difference is where the runs come from. All mapping logic is in `runs_to_fragments`, which is dict-driven and has full unit-test coverage (`tests/unit/test_adapter_langsmith.py`).

## Comparison to the named-incident example

The companion `examples/replit_drop_database/` reconstructs a **hand-authored manifest** describing what a public-postmortem reader can recover from a single-agent **cross-stack** incident. That example deliberately lacks `policy_snapshot` and `config_snapshot` because the public record never disclosed them — the reconstructor correctly reports those properties as `structurally_unfillable` (57.1% completeness).

This LangSmith example shows the opposite end of the spectrum: a well-governed in-stack deployment where the operator chose to record policy and config snapshots, and the same instrument scores 94.3%. The difference between 57.1% and 94.3% is the *evidence regime*: same instrument, different inputs, faithful per-property accounting in both directions.
