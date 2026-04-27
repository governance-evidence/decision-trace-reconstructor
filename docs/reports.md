# Reports

`decision-trace reconstruct fragments.json --out report/ --jsonld` writes the reconstruction outputs into the target directory.

```text
report/
├── feasibility.json    # per-property reconstructability tensor
├── trace.jsonld        # W3C PROV-O graph
└── summary.txt         # optional human-readable narrative in worked examples
```

## `feasibility.json`

`feasibility.json` is the primary artifact. Each decision-event-schema property is classified as one of:

- `fully_fillable`: enough evidence exists to reconstruct the property
- `partially_fillable`: evidence exists, but part of the property is missing
- `structurally_unfillable`: the trace format never recorded the required signal
- `opaque`: internal model reasoning cannot be reconstructed from external logs

Each property also carries a `gap` field. When the property is not fully fillable, `gap` explains the missing signal in natural language. The aggregate `completeness_pct` supports cross-trace comparison, and `dominant_break` identifies the strongest operational failure mode when one is visible.

## `trace.jsonld`

`trace.jsonld` represents the same reconstruction as a W3C PROV-O JSON-LD graph. The context is self-contained, so validation does not require a network fetch.

The SPARQL example below requires `rdflib`; install it with `pip install 'decision-trace-reconstructor[prov]'` or, from a repository checkout, `pip install -e '.[prov]'`.

```python
from rdflib import Graph

g = Graph()
g.parse("report/trace.jsonld", format="json-ld")

q = """
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX demm: <https://decisiontrace.org/demm/v1#>
PREFIX schema: <https://decisiontrace.org/schema/v1#>
SELECT ?unit WHERE {
  ?unit a demm:DecisionUnit ;
        demm:perPropertyFeasibility ?feas .
  ?feas demm:property schema:policy_basis ;
        demm:category "structurally_unfillable" .
}
"""

for row in g.query(q):
    print(row)
```

## Related

- [Reconstruction architecture](architecture.md)
- [Adapter documentation](adapters/README.md)
