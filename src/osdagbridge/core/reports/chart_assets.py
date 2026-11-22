"""Data-driven charts embedded in the generated design report."""

from __future__ import annotations

import math
import os
from typing import Any

from .styles import COLORS


def _number(value: Any) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def _max_ur(values) -> float | None:
    clean = [number for value in values if (number := _number(value)) is not None and number >= 0]
    return max(clean) if clean else None


def _walk_key_values(value, key_words):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(word in lowered for word in key_words):
                number = _number(child)
                if number is not None and number >= 0:
                    found.append(number)
            found.extend(_walk_key_values(child, key_words))
    elif isinstance(value, (list, tuple)):
        for child in value:
            found.extend(_walk_key_values(child, key_words))
    return found


def _utilization_data(output: dict) -> tuple[list[str], list[float | None]]:
    design = output.get("design_results") or {}
    per_girder = design.get("per_girder") or {}
    girder_urs = []
    for girder, data in per_girder.items():
        if str(girder).startswith("EB"):
            continue
        girder_urs.extend(chk.get("dcr") for chk in (data.get("checks") or []))
        for lc, lc_data in (data.get("per_lc") or {}).items():
            if not str(lc).lower().startswith("envelope"):
                girder_urs.extend(chk.get("dcr") for chk in (lc_data.get("checks") or []))

    deck = output.get("deck_design_results") or {}
    deck_urs = [value for key, value in deck.items() if str(key).lower().startswith("ur_")]
    bracing = output.get("crossbracing_design_results") or {}
    bracing_urs = _walk_key_values(bracing, ("efficiency", "utilization", "dcr", "ur"))
    diaphragm_design = output.get("end_diaphragm_design_results") or {}
    diaphragm = _walk_key_values(diaphragm_design, ("efficiency", "utilization", "dcr", "ur"))
    return (
        ["Steel plate girders", "Concrete deck slab", "Cross bracing", "End diaphragms"],
        [_max_ur(girder_urs), _max_ur(deck_urs), _max_ur(bracing_urs), _max_ur(diaphragm)],
    )


def _material_data(inputs: dict) -> tuple[list[float | None], list[float | None]]:
    girders = _number(inputs.get("steel_girders_wt_total"))
    bracing_parts = [_number(inputs.get(f"bracing_{part}_wt_total")) for part in ("top", "bot", "diag")]
    bracing = sum(value for value in bracing_parts if value is not None) if any(value is not None for value in bracing_parts) else None
    end_diaphragms = _number(inputs.get("end_diaphragm_wt_total"))
    steel = [girders, bracing, end_diaphragms]
    concrete = _number(inputs.get("concrete_deck_vol_total"))
    rebar = _number(inputs.get("rebar_deck_wt_total"))
    return steel, [concrete, rebar]


def generate_report_charts(output: dict, inputs: dict, image_dir: str) -> dict[str, str]:
    """Create temporary chart PNGs and return their paths by report section."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    os.makedirs(image_dir, exist_ok=True)
    paths = {}
    labels, ratios = _utilization_data(output)
    fig, ax = plt.subplots(figsize=(8.0, 3.7))
    x = np.arange(len(labels))
    valid = [(i, value) for i, value in enumerate(ratios) if value is not None]
    missing = [i for i, value in enumerate(ratios) if value is None]
    if valid:
        ax.bar([i for i, _ in valid], [value for _, value in valid], color="#" + COLORS["chart_blue"], width=0.62)
        for i, value in valid:
            ax.annotate(f"{value:.2f}", (i, value), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9)
    for i in missing:
        ax.text(i, 0.04, "N/A", ha="center", va="bottom", color="#666666", fontsize=9)
    ax.axhline(1.0, color=f"#{COLORS['fail']}", linestyle="--", linewidth=1.5, label="UR = 1.0 limit")
    ymax = max([1.12] + [value * 1.16 for _, value in valid])
    ax.set_ylim(0, ymax)
    ax.set_xlim(-0.6, len(labels) - 0.4)
    ax.set_xticks(x, labels, rotation=12, ha="right")
    ax.set_ylabel("Utilization Ratio")
    ax.set_title("Overall Design Utilization Ratios")
    ax.grid(axis="y", color="#D9DDE1", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    paths["utilization"] = os.path.join(image_dir, "utilization_summary.png")
    fig.savefig(paths["utilization"], dpi=180, bbox_inches="tight")
    plt.close(fig)

    steel, civil = _material_data(inputs)
    fig, ax = plt.subplots(figsize=(7.8, 3.5))
    items = ["Girders", "Cross bracing", "End diaphragms"]
    valid_steel = [(i, value) for i, value in enumerate(steel) if value is not None]
    missing_steel = [i for i, value in enumerate(steel) if value is None]
    if valid_steel:
        ax.bar([i for i, _ in valid_steel], [value for _, value in valid_steel], color="#" + COLORS["chart_green"], width=0.62)
        for i, value in valid_steel:
            ax.annotate(f"{value:.2f}", (i, value), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9)
    for i in missing_steel:
        ax.text(i, 0.02, "N/A", ha="center", va="bottom", color="#666666", fontsize=9)
    ax.set_xticks(range(3), items, rotation=10, ha="right")
    ax.set_xlim(-0.6, 2.4)
    ax.set_ylabel("Structural steel (MT)")
    ax.set_title("Structural Steel Quantity")
    ax.grid(axis="y", color="#D9DDE1", linewidth=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    paths["steel_quantity"] = os.path.join(image_dir, "steel_quantities.png")
    fig.savefig(paths["steel_quantity"], dpi=180, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.8, 3.5))
    labels = ["Concrete deck", "Reinforcement steel"]
    for i, value in enumerate(civil):
        if value is None:
            ax.text(i, 0.02, "N/A", ha="center", va="bottom", color="#666666", fontsize=9)
        else:
            ax.bar(i, value, color="#" + [COLORS["chart_orange"], COLORS["chart_blue"]][i], width=0.62)
            ax.annotate(f"{value:.2f}", (i, value), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9)
    ax.set_xticks(range(2), labels, rotation=10, ha="right")
    ax.set_xlim(-0.6, 1.6)
    ax.set_ylabel("Quantity")
    ax.set_title("Concrete and Reinforcement Quantities")
    ax.grid(axis="y", color="#D9DDE1", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.text(0, -0.24, "Concrete: m³", transform=ax.get_xaxis_transform(), ha="center", fontsize=8)
    ax.text(1, -0.24, "Reinforcement: MT", transform=ax.get_xaxis_transform(), ha="center", fontsize=8)
    fig.tight_layout()
    paths["concrete_rebar_quantity"] = os.path.join(image_dir, "concrete_rebar_quantities.png")
    fig.savefig(paths["concrete_rebar_quantity"], dpi=180, bbox_inches="tight")
    plt.close(fig)
    return paths
