# Roadmap

## Adapter Roadmap

Planned adapter:

- `anthropic_managed` — Anthropic Managed Agents admin API, once the API reaches stable status

## Adding an Adapter

Follow the existing adapter package shape:

- `src/reconstructor/adapters/<adapter>/`
- `tests/unit/adapters/<adapter>/`
- `examples/<adapter>_basic_agent/`
- `docs/adapters/<adapter>.md`

Open an issue or a draft PR with the target trace format and a small redacted sample.

## Related

- [Adapter documentation](adapters/README.md)
- [Development](development.md)
