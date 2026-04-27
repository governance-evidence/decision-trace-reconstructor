"""Console table rendering for the synthetic evaluation."""

from __future__ import annotations

from typing import Any


def _print_tables(cells: list[dict[str, Any]], per_property: dict[str, dict[str, float]]) -> None:
    arch_order = ("single_agent", "multi_agent", "human_in_the_loop", "non_agentic")
    lookup = {(c["architecture"], c["stack_tier"]): c for c in cells}
    _print_completeness_table(lookup, arch_order)
    _print_boundary_table(lookup, arch_order)
    _print_mode_table(lookup, arch_order)
    _print_property_table(per_property)


def _print_completeness_table(
    lookup: dict[tuple[Any, Any], dict[str, Any]],
    arch_order: tuple[str, ...],
) -> None:
    print()
    print("Table 4. Reconstruction completeness (% mean [95% CI])")
    print(f"{'Architecture':<22} | {'Within-stack':<25} | {'Cross-stack':<25}")
    for arch in arch_order[:-1]:
        line = f"{arch:<22} |"
        for tier in ("within_stack", "cross_stack"):
            c = lookup.get((arch, tier))
            if c:
                line += f" {c['completeness_pct']:>5}% [{c['completeness_ci_low']:.1f}, {c['completeness_ci_high']:.1f}]   |"
            else:
                line += f" {'n/a':<25}|"
        print(line)
    baseline = lookup.get(("non_agentic", "within_stack"))
    if baseline:
        print(
            f"{'non_agentic baseline':<22} | "
            f"{baseline['completeness_pct']:>5}% [{baseline['completeness_ci_low']:.1f}, {baseline['completeness_ci_high']:.1f}]   | {'--':<25}"
        )


def _print_boundary_table(
    lookup: dict[tuple[Any, Any], dict[str, Any]],
    arch_order: tuple[str, ...],
) -> None:
    print()
    print("Table 5. Boundary-detection F1 (mean)")
    print(f"{'Architecture':<22} | {'Within-stack':<15} | {'Cross-stack':<15}")
    for arch in arch_order[:-1]:
        line = f"{arch:<22} |"
        for tier in ("within_stack", "cross_stack"):
            c = lookup.get((arch, tier))
            if c:
                line += f" {c['boundary_f1']:<14} |"
            else:
                line += f" {'n/a':<14} |"
        print(line)


def _print_mode_table(
    lookup: dict[tuple[Any, Any], dict[str, Any]],
    arch_order: tuple[str, ...],
) -> None:
    print()
    print("Table 6. 7-mode dominance (modal_mode, share, dominant_break)")
    for arch in arch_order[:-1]:
        for tier in ("within_stack", "cross_stack"):
            c = lookup.get((arch, tier))
            if c:
                print(
                    f"  {arch:<20} x {tier:<14} -> mode={c['modal_mode']}, share={c['modal_mode_share']:.2f}, break={c['dominant_break']}"
                )


def _print_property_table(per_property: dict[str, dict[str, float]]) -> None:
    print()
    print("Table 8. Per-decision-event-property feasibility distribution (% of slots)")
    header = (
        f"{'property':<22} | {'fully':<7} | {'partial':<7} | {'struct_unfill':<13} | {'opaque':<7}"
    )
    print(header)
    for prop, dist in per_property.items():
        print(
            f"{prop:<22} | {dist.get('fully_fillable', 0):>5.1f} | "
            f"{dist.get('partially_fillable', 0):>5.1f} | "
            f"{dist.get('structurally_unfillable', 0):>11.1f} | "
            f"{dist.get('opaque', 0):>5.1f}"
        )
