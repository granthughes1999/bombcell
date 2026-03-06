from pathlib import Path
import re
from typing import Any, Dict
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import sys
import numpy as np
import pandas as pd
import importlib
import subprocess
import os
import bombcell as bc

def load_geometry(ks_dir: Path):
    ks_dir = Path(ks_dir)
    pos = np.load(ks_dir / "channel_positions.npy")

    cmap_file = ks_dir / "channel_map.npy"
    if cmap_file.exists():
        cmap = np.load(cmap_file).squeeze()
    else:
        cmap = None

    if pos.ndim != 2 or pos.shape[1] != 2:
        raise ValueError(f"Expected (n_channels,2) channel_positions in {ks_dir}, got {pos.shape}")

    return pos, cmap


def nearest_neighbor_distances(channel_positions):
    cp = np.asarray(channel_positions, dtype=float)
    d = cp[:, None, :] - cp[None, :, :]
    dist = np.sqrt((d**2).sum(axis=2))
    np.fill_diagonal(dist, np.inf)
    return dist.min(axis=1)


def summarize_geometry(channel_positions):
    cp = np.asarray(channel_positions, dtype=float)
    ux = np.unique(np.round(cp[:, 0], 6))
    uy = np.unique(np.round(cp[:, 1], 6))

    dx = np.diff(np.sort(ux)) if ux.size > 1 else np.array([])
    dy = np.diff(np.sort(uy)) if uy.size > 1 else np.array([])
    nn = nearest_neighbor_distances(cp)

    summary = {
        "n_channels": cp.shape[0],
        "n_unique_x": int(ux.size),
        "n_unique_y": int(uy.size),
        "median_dx": float(np.median(dx)) if dx.size else np.nan,
        "median_dy": float(np.median(dy)) if dy.size else np.nan,
        "median_nn_dist": float(np.median(nn)),
        "p90_nn_dist": float(np.percentile(nn, 90)),
    }
    return summary, nn


def suggest_nChannelsIsoDist(summary):
    """
    Heuristic suggestion:
    - sparse maps (large nearest-neighbor spacing) -> larger neighborhood
    - dense maps -> default is often fine
    """
    p90 = summary["p90_nn_dist"]
    if np.isnan(p90):
        return "unknown", "Could not estimate spacing"
    if p90 >= 40:
        return "8-12", "Sparse/interleaved geometry: use more nearby channels"
    if p90 >= 25:
        return "6-8", "Moderately sparse geometry: consider increasing from default 4"
    return "4-6", "Dense geometry: default 4 is usually reasonable"


def plot_geometry(channel_positions, title="",probe=None,save_dir=None):
    cp = np.asarray(channel_positions)
    fig, ax = plt.subplots(figsize=(5, 9))
    ax.scatter(cp[:, 0], cp[:, 1], s=14)
    ax.set_xlabel("x (um)")
    ax.set_ylabel("y (um)")
    ax.set_title(title)
    ax.grid(alpha=0.2)
    ax.set_aspect('equal')
    out_path = Path(save_dir) / f"probe_{probe}_geometry.png"
    fig.savefig(out_path)
    print(f"Saved geometry plot for probe {probe} to: {out_path}")
    plt.show()


def compute_tip_distance_um(y_values, shank_y, tip_position: str = "max_y"):
    """Mirror the tip-distance logic used in run_bombcell_unified.py."""
    y_values = np.asarray(y_values, dtype=float)
    shank_y = np.asarray(shank_y, dtype=float)

    if tip_position == "min_y":
        return y_values - float(np.nanmin(shank_y))
    if tip_position == "max_y":
        return float(np.nanmax(shank_y)) - y_values
    raise ValueError("tip_position must be 'min_y' or 'max_y'.")


def region_to_label_suffix(region_name, fallback: str = "BRAINREGION") -> str:
    if region_name is None:
        return fallback

    text = str(region_name).strip()
    if not text:
        return fallback

    # Prefer abbreviation inside parentheses, e.g. "(... STIM)" -> "STIM".
    match = re.search(r"\(([^)]+)\)", text)
    token = match.group(1) if match else text
    suffix = re.sub(r"[^A-Za-z0-9]+", "_", token).strip("_").upper()
    return suffix if suffix else fallback


def _estimate_spacing(values, default_value: float) -> float:
    vals = np.unique(np.round(np.asarray(values, dtype=float), 6))
    if vals.size < 2:
        return float(default_value)

    diffs = np.diff(np.sort(vals))
    diffs = diffs[diffs > 0]
    if diffs.size == 0:
        return float(default_value)
    return float(np.median(diffs))


# Brain-region logic mirrored from add_brain_region_to_phy.ipynb
PROBE_A_REGION_RANGES_UM = {
    "IP": (0.0, 650.0),
    "SIM": (900.0, 3250.0),
}
PROBE_TO_REGION_ALIAS = {
    "B": "PG",
    "C": "MoP",
    "D": "VaL",
    "E": "SnR",
    "F": "RN",
}
REGION_BAND_COLORS = {
    "IP": "#4C78A8",
    "SIM": "#F58518",
    "PG": "#54A24B",
    "MOP": "#E45756",
    "VAL": "#72B7B2",
    "SNR": "#EECA3B",
    "RN": "#B279A2",
}


def _resolve_region_alias(probe_letter: str, probe_brain_regions: Dict[str, str]):
    if probe_letter in PROBE_TO_REGION_ALIAS:
        return PROBE_TO_REGION_ALIAS[probe_letter]

    region_name = probe_brain_regions.get(probe_letter)
    return region_to_label_suffix(region_name)


def get_brain_region_depth_bands(
    probe_letter: str,
    roi_end_um: float,
    probe_brain_regions: Dict[str, str],
):
    bands = []
    roi_end_um = float(roi_end_um)

    if probe_letter == "A":
        for region_name, (start_um, end_um) in PROBE_A_REGION_RANGES_UM.items():
            start_um = max(0.0, float(start_um))
            end_um = min(float(end_um), roi_end_um)
            if end_um >= start_um:
                bands.append(
                    {
                        "region": region_name,
                        "start_um": start_um,
                        "end_um": end_um,
                    }
                )
    else:
        region_name = _resolve_region_alias(probe_letter, probe_brain_regions)
        bands.append(
            {
                "region": region_name,
                "start_um": 0.0,
                "end_um": roi_end_um,
            }
        )

    return bands


def compute_channel_roi_region_labels(
    channel_positions,
    probe_letter: str,
    roi_end_um: float,
    tip_position: str = "max_y",
    out_label: str = "OUT_ROI",
    probe_brain_regions: Dict[str, str] = None,
):
    cp = np.asarray(channel_positions, dtype=float)
    if cp.ndim != 2 or cp.shape[1] != 2:
        raise ValueError(f"Expected (n_channels,2) channel_positions, got {cp.shape}")

    if probe_brain_regions is None:
        probe_brain_regions = {}

    shank_y = cp[:, 1].astype(float)
    depth_um = compute_tip_distance_um(shank_y, shank_y, tip_position=tip_position)
    in_roi_mask = depth_um <= float(roi_end_um)

    region_labels = np.full(cp.shape[0], "", dtype=object)
    region_bands = get_brain_region_depth_bands(
        probe_letter=probe_letter,
        roi_end_um=roi_end_um,
        probe_brain_regions=probe_brain_regions,
    )
    for band in region_bands:
        in_region = (
            in_roi_mask
            & (depth_um >= float(band["start_um"]))
            & (depth_um <= float(band["end_um"]))
        )
        region_labels[in_region] = str(band["region"])

    roi_labels = np.full(cp.shape[0], out_label, dtype=object)
    in_idx = np.where(in_roi_mask)[0]
    for idx in in_idx:
        region = str(region_labels[idx]).strip()
        if region:
            roi_labels[idx] = f"IN_ROI_{region.upper()}"
        else:
            roi_labels[idx] = "IN_ROI_UNASSIGNED"

    return {
        "depth_um": depth_um,
        "in_roi_mask": in_roi_mask,
        "region_labels": region_labels,
        "roi_labels": roi_labels,
        "region_bands": region_bands,
    }


def _region_band_color(region_name: str):
    key = str(region_name).upper()
    return REGION_BAND_COLORS.get(key, "#7F7F7F")


def _resolve_plot_save_path(
    save_dir,
    function_name: str,
    probe_letter: str,
    filename: str,
):
    base_dir = Path(save_dir) / "NP_Channel_Verification" / str(function_name)
    if not base_dir.exists():
        base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / filename


def _find_kslabel_col(df: pd.DataFrame):
    for c in ["KSlabel", "KSLabel", "kslabel", "ks_label", "label", "quality"]:
        if c in df.columns:
            return c
    return None


def _normalize_bc_unit_label(value):
    if pd.isna(value):
        return np.nan
    return str(value).strip().upper()


def _normalize_ks_unit_label(value):
    if pd.isna(value):
        return np.nan
    try:
        iv = int(float(value))
        if iv == 2:
            return "good"
        if iv == 1:
            return "mua"
    except Exception:
        pass

    text = str(value).strip().lower()
    if text in {"2", "good", "single", "singleunit", "single_unit"}:
        return "good"
    if text in {"1", "mua", "multi", "multiunit", "multi_unit"}:
        return "mua"
    return text


def _normalize_unit_filter_values(filter_values, unit_filter_source: str):
    if filter_values is None:
        return None

    if isinstance(filter_values, str):
        raw_values = [filter_values]
    else:
        raw_values = list(filter_values)

    if unit_filter_source == "bombcell":
        return {_normalize_bc_unit_label(v) for v in raw_values}
    return {_normalize_ks_unit_label(v) for v in raw_values}


def _resolve_unit_channel_counts(
    unit_data,
    n_channels: int,
    unit_filter_source: str = "bombcell",
    unit_filter_values=None,
    max_channel_col: str = None,
):
    if unit_data is None:
        raise ValueError("unit_data is required when show_unit_location=True.")

    units_df = unit_data.copy() if isinstance(unit_data, pd.DataFrame) else pd.DataFrame(unit_data)
    if units_df.empty:
        return pd.Series(dtype=int), {"filter_source": unit_filter_source, "filter_values": []}

    source = str(unit_filter_source).strip().lower()
    if source in {"ks", "kilosort", "kilosort4"}:
        source = "kilosort4"
    elif source != "bombcell":
        raise ValueError("unit_filter_source must be 'bombcell' or 'kilosort4'.")

    if max_channel_col is None:
        for candidate in ["maxChannels", "maxChannel", "max_channel", "peak_channel", "peakChannel"]:
            if candidate in units_df.columns:
                max_channel_col = candidate
                break
    if max_channel_col is None or max_channel_col not in units_df.columns:
        raise KeyError(
            "Could not find a channel column for unit overlay. "
            "Expected one of: maxChannels, maxChannel, max_channel, peak_channel, peakChannel."
        )

    if source == "bombcell":
        label_col = "bc_label" if "bc_label" in units_df.columns else "bc_classificationReason"
        if label_col not in units_df.columns:
            raise KeyError(
                "Bombcell unit overlay requires a 'bc_label' or 'bc_classificationReason' column."
            )
        units_df["_unit_overlay_label"] = units_df[label_col].map(_normalize_bc_unit_label)
    else:
        label_col = _find_kslabel_col(units_df)
        if label_col is None:
            raise KeyError(
                "Kilosort4 unit overlay requires a KS label column such as KSLabel or ks_label."
            )
        units_df["_unit_overlay_label"] = units_df[label_col].map(_normalize_ks_unit_label)

    filter_values = _normalize_unit_filter_values(unit_filter_values, source)
    if filter_values is not None:
        units_df = units_df[units_df["_unit_overlay_label"].isin(filter_values)].copy()

    units_df["_unit_overlay_channel"] = pd.to_numeric(units_df[max_channel_col], errors="coerce")
    units_df = units_df.dropna(subset=["_unit_overlay_channel"]).copy()
    units_df["_unit_overlay_channel"] = units_df["_unit_overlay_channel"].astype(int)
    units_df = units_df[
        (units_df["_unit_overlay_channel"] >= 0) & (units_df["_unit_overlay_channel"] < int(n_channels))
    ].copy()

    counts = units_df["_unit_overlay_channel"].value_counts().sort_index()
    return counts, {
        "filter_source": source,
        "filter_values": sorted([] if filter_values is None else filter_values),
        "label_col": label_col,
        "max_channel_col": max_channel_col,
    }


def plot_roi_channel_comparison(
    channel_positions,
    probe_letter: str,
    roi_end_um: float,
    out_label: str = "OUT_ROI",
    probe_brain_regions: Dict[str, str] = None,
    save_dir: str = None,
    show_plt: bool = True
):
    cp = np.asarray(channel_positions, dtype=float)
    x_um = cp[:, 0].astype(float)

    if probe_brain_regions is None:
        probe_brain_regions = {}

    x_spacing = _estimate_spacing(x_um, default_value=16.0)
    y_spacing = _estimate_spacing(cp[:, 1], default_value=15.0)
    box_w = max(8.0, 1.6 * x_spacing)
    box_h = max(8.0, 1.6 * y_spacing)
    x_pad = max(40.0, 3.0 * x_spacing)
    x_text = float(np.nanmax(x_um) + 0.55 * x_pad)

    full_depth_um = compute_tip_distance_um(cp[:, 1], cp[:, 1], tip_position="min_y")
    y_top_pad = max(30.0, 4.0 * y_spacing)
    y_bottom_pad = max(8.0, 0.8 * y_spacing)
    y_limits = (
        float(np.nanmin(full_depth_um) - y_bottom_pad),
        float(np.nanmax(full_depth_um) + y_top_pad),
    )

    fig, axes = plt.subplots(1, 2, figsize=(13, 8), sharex=True, sharey=True, constrained_layout=False)
    tip_positions = ("min_y", "max_y")
    details = {}

    for i, tip_position in enumerate(tip_positions):
        ax = axes[i]
        info = compute_channel_roi_region_labels(
            cp,
            probe_letter=probe_letter,
            roi_end_um=roi_end_um,
            tip_position=tip_position,
            out_label=out_label,
            probe_brain_regions=probe_brain_regions,
        )
        details[tip_position] = info
        in_mask = info["in_roi_mask"]
        depth_um = info["depth_um"]

        # Draw region depth windows first to show where each brain region sits along the probe.
        for band in info["region_bands"]:
            region_name = str(band["region"])
            color = _region_band_color(region_name)
            y0 = float(band["start_um"])
            y1 = float(band["end_um"])
            ax.axhspan(y0, y1, facecolor=color, edgecolor="none", alpha=0.10, zorder=-3)
            ax.text(
                x_text,
                0.5 * (y0 + y1),
                region_name,
                ha="left",
                va="center",
                fontsize=8,
                color=color,
                fontweight="bold",
                clip_on=False,
            )

        # Large shaded boxes behind exact IN_ROI channels.
        for x0, y0 in zip(x_um[in_mask], depth_um[in_mask]):
            ax.add_patch(
                Rectangle(
                    (x0 - box_w / 2.0, y0 - box_h / 2.0),
                    box_w,
                    box_h,
                    facecolor="green",
                    edgecolor="none",
                    alpha=0.18,
                    zorder=0,
                )
            )

        ax.scatter(
            x_um[~in_mask],
            depth_um[~in_mask],
            s=24,
            color="red",
            label=out_label if i == 0 else None,
            zorder=2,
        )
        ax.scatter(
            x_um[in_mask],
            depth_um[in_mask],
            s=28,
            color="green",
            label="IN_ROI_*" if i == 0 else None,
            zorder=3,
        )

        ax.axhline(float(roi_end_um), color="black", linewidth=1.2, linestyle="--", alpha=0.8)
        ax.set_title(f"{probe_letter} | tip_position='{tip_position}'", pad=18)
        ax.set_xlabel("x (um)")
        ax.set_xlim(float(np.nanmin(x_um) - 0.35 * x_pad), float(np.nanmax(x_um) + 1.15 * x_pad))
        ax.set_ylim(*y_limits)
        ax.grid(alpha=0.2)

    axes[0].set_ylabel("Depth from tip (um)")
    fig.suptitle(f"Probe {probe_letter}: ROI + brain-region map by tip convention", fontsize=12, y=0.985)

    handles, labels = axes[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.955), ncol=2, frameon=False)

    fig.subplots_adjust(top=0.84, wspace=0.18)

    if save_dir is not None:
        save_path = _resolve_plot_save_path(
            save_dir=save_dir,
            function_name="plot_roi_channel_comparison",
            probe_letter=probe_letter,
            filename=f"{probe_letter}_roi_cmp.png",
        )
        fig.savefig(save_path, dpi=300)
        print(f"Saved ROI/brain-region map for probe {probe_letter} to: {save_path}")
    if show_plt:
        plt.show()
    return details


def plot_roi_channel_comparison_min_y(
    channel_positions,
    probe_letter: str,
    roi_end_um: float,
    out_label: str = "OUT_ROI",
    probe_brain_regions: Dict[str, str] = None,
    show_plt: bool = True,
    save_dir: str = None,
    show_unit_location: bool = False,
    unit_data=None,
    unit_filter_source: str = "bombcell",
    unit_filter_values=None,
    max_channel_col: str = None,
):
    """
    Plot a single ROI map using the min_y tip convention.

    Optional unit overlays use `unit_data` rows with a channel column such as
    `maxChannels`. Filters can target Bombcell labels (`GOOD`, `MUA`, `NOISE`)
    or Kilosort4 labels (`good`, `mua`).
    """
    cp = np.asarray(channel_positions, dtype=float)
    x_um = cp[:, 0].astype(float)

    if probe_brain_regions is None:
        probe_brain_regions = {}

    x_spacing = _estimate_spacing(x_um, default_value=16.0)
    y_spacing = _estimate_spacing(cp[:, 1], default_value=15.0)
    box_w = max(8.0, 1.6 * x_spacing)
    box_h = max(8.0, 1.6 * y_spacing)
    x_pad = max(40.0, 3.0 * x_spacing)
    x_text = float(np.nanmax(x_um) + 0.55 * x_pad)

    full_depth_um = compute_tip_distance_um(cp[:, 1], cp[:, 1], tip_position="min_y")
    y_top_pad = max(30.0, 4.0 * y_spacing)
    y_bottom_pad = max(8.0, 0.8 * y_spacing)
    y_limits = (
        float(np.nanmin(full_depth_um) - y_bottom_pad),
        float(np.nanmax(full_depth_um) + y_top_pad),
    )

    fig, ax = plt.subplots(1, 1, figsize=(8, 8), constrained_layout=False)
    info = compute_channel_roi_region_labels(
        cp,
        probe_letter=probe_letter,
        roi_end_um=roi_end_um,
        tip_position="min_y",
        out_label=out_label,
        probe_brain_regions=probe_brain_regions,
    )
    in_mask = info["in_roi_mask"]
    depth_um = info["depth_um"]

    for band in info["region_bands"]:
        region_name = str(band["region"])
        color = _region_band_color(region_name)
        y0 = float(band["start_um"])
        y1 = float(band["end_um"])
        ax.axhspan(y0, y1, facecolor=color, edgecolor="none", alpha=0.10, zorder=-3)
        ax.text(
            x_text,
            0.5 * (y0 + y1),
            region_name,
            ha="left",
            va="center",
            fontsize=8,
            color=color,
            fontweight="bold",
            clip_on=False,
        )

    for x0, y0 in zip(x_um[in_mask], depth_um[in_mask]):
        ax.add_patch(
            Rectangle(
                (x0 - box_w / 2.0, y0 - box_h / 2.0),
                box_w,
                box_h,
                facecolor="green",
                edgecolor="none",
                alpha=0.18,
                zorder=0,
            )
        )

    ax.scatter(
        x_um[~in_mask],
        depth_um[~in_mask],
        s=24,
        color="red",
        label=out_label,
        zorder=2,
    )
    ax.scatter(
        x_um[in_mask],
        depth_um[in_mask],
        s=28,
        color="green",
        label="IN_ROI_*",
        zorder=3,
    )

    overlay_meta = None
    unit_channel_counts = pd.Series(dtype=int)
    if show_unit_location:
        unit_channel_counts, overlay_meta = _resolve_unit_channel_counts(
            unit_data=unit_data,
            n_channels=cp.shape[0],
            unit_filter_source=unit_filter_source,
            unit_filter_values=unit_filter_values,
            max_channel_col=max_channel_col,
        )
        if not unit_channel_counts.empty:
            overlay_idx = unit_channel_counts.index.to_numpy(dtype=int)
            overlay_counts = unit_channel_counts.to_numpy(dtype=float)
            overlay_sizes = 80.0 + 65.0 * np.sqrt(overlay_counts)
            overlay_label = f"Units ({overlay_meta['filter_source']})"
            if len(overlay_meta["filter_values"]) > 0:
                overlay_label = (
                    f"Units ({overlay_meta['filter_source']}: "
                    + ", ".join(map(str, overlay_meta["filter_values"]))
                    + ")"
                )
            ax.scatter(
                x_um[overlay_idx],
                depth_um[overlay_idx],
                s=overlay_sizes,
                facecolors="green",
                edgecolors="green",
                alpha=0.22,
                linewidths=1.0,
                label=overlay_label,
                zorder=4,
            )

    ax.axhline(float(roi_end_um), color="black", linewidth=1.2, linestyle="--", alpha=0.8)
    ax.set_title(f"{probe_letter} | tip_position='min_y'", pad=18)
    ax.set_xlabel("x (um)")
    ax.set_ylabel("DEPTH (um)")
    ax.set_xlim(float(np.nanmin(x_um) - 0.35 * x_pad), float(np.nanmax(x_um) + 1.15 * x_pad))
    ax.set_ylim(*y_limits)
    ax.grid(alpha=0.2)

    right_ax = ax.twinx()
    channel_ticks = np.arange(0, cp.shape[0], 20, dtype=int)
    tick_table = (
        pd.DataFrame({"channel": channel_ticks, "depth": depth_um[channel_ticks]})
        .dropna(subset=["depth"])
        .sort_values(["depth", "channel"])
        .drop_duplicates(subset=["depth"], keep="first")
    )
    right_ax.set_ylim(ax.get_ylim())
    right_ax.set_yticks(tick_table["depth"].to_numpy(dtype=float))
    right_ax.set_yticklabels([str(int(ch)) for ch in tick_table["channel"].tolist()])
    right_ax.set_ylabel("Channel # (every 20)")
    right_ax.grid(False)

    fig.suptitle(f"Probe {probe_letter}: ROI + brain-region map (min_y)", fontsize=12, y=0.985)

    handles, labels = ax.get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.955), ncol=2, frameon=False)

    fig.subplots_adjust(top=0.84)

    if save_dir is not None:
        save_path = _resolve_plot_save_path(
            save_dir=save_dir,
            function_name="plot_roi_channel_comparison_min_y",
            probe_letter=probe_letter,
            filename=f"{probe_letter}_miny.png",
        )
        fig.savefig(save_path, dpi=300)
        print(f"Saved min_y ROI/brain-region map for probe {probe_letter} to: {save_path}")
        
    if show_plt:
        plt.show()

    info["unit_channel_counts"] = unit_channel_counts.to_dict()
    info["unit_overlay_meta"] = overlay_meta
    return info


def plot_roi_channel_comparison_min_y_true_aspect(
    channel_positions,
    probe_letter: str,
    roi_end_um: float,
    out_label: str = "OUT_ROI",
    probe_brain_regions: Dict[str, str] = None,
    show_plt: bool = True,
    save_dir: str = None,
    show_unit_location: bool = False,
    unit_data=None,
    unit_filter_source: str = "bombcell",
    unit_filter_values=None,
    max_channel_col: str = None,
):
    """
    Plot the min_y ROI map using equal x/y scaling in physical units.

    This preserves the true Neuropixels geometry so the shank appears as a
    narrow line rather than as separated x-columns.
    """
    cp = np.asarray(channel_positions, dtype=float)
    x_um = cp[:, 0].astype(float)

    if probe_brain_regions is None:
        probe_brain_regions = {}

    x_spacing = _estimate_spacing(x_um, default_value=16.0)
    y_spacing = _estimate_spacing(cp[:, 1], default_value=15.0)
    x_pad = max(8.0, 0.8 * x_spacing)
    x_limits = (
        float(np.nanmin(x_um) - x_pad),
        float(np.nanmax(x_um) + x_pad),
    )

    full_depth_um = compute_tip_distance_um(cp[:, 1], cp[:, 1], tip_position="min_y")
    y_top_pad = max(30.0, 4.0 * y_spacing)
    y_bottom_pad = max(8.0, 0.8 * y_spacing)
    y_limits = (
        float(np.nanmin(full_depth_um) - y_bottom_pad),
        float(np.nanmax(full_depth_um) + y_top_pad),
    )

    x_span = max(1.0, x_limits[1] - x_limits[0])
    y_span = max(1.0, y_limits[1] - y_limits[0])
    true_aspect = y_span / x_span
    fig_height = min(28.0, max(12.0, 0.22 * true_aspect))

    fig, ax = plt.subplots(1, 1, figsize=(5.8, fig_height), constrained_layout=False)
    info = compute_channel_roi_region_labels(
        cp,
        probe_letter=probe_letter,
        roi_end_um=roi_end_um,
        tip_position="min_y",
        out_label=out_label,
        probe_brain_regions=probe_brain_regions,
    )
    in_mask = info["in_roi_mask"]
    depth_um = info["depth_um"]

    for band in info["region_bands"]:
        region_name = str(band["region"])
        color = _region_band_color(region_name)
        y0 = float(band["start_um"])
        y1 = float(band["end_um"])
        ax.axhspan(y0, y1, facecolor=color, edgecolor="none", alpha=0.10, zorder=-3)
        ax.text(
            1.03,
            0.5 * (y0 + y1),
            region_name,
            transform=ax.get_yaxis_transform(),
            ha="left",
            va="center",
            fontsize=8,
            color=color,
            fontweight="bold",
            clip_on=False,
        )

    # In true-aspect view the shank is physically very narrow, so large data-unit
    # rectangles hide many channels. Use a slim ROI highlight band instead.
    ax.axhspan(0.0, float(roi_end_um), facecolor="green", edgecolor="none", alpha=0.05, zorder=-2)

    ax.scatter(
        x_um[~in_mask],
        depth_um[~in_mask],
        s=5,
        color="red",
        label=out_label,
        zorder=2,
    )
    ax.scatter(
        x_um[in_mask],
        depth_um[in_mask],
        s=7,
        color="green",
        label="IN_ROI_*",
        zorder=3,
    )

    overlay_meta = None
    unit_channel_counts = pd.Series(dtype=int)
    if show_unit_location:
        unit_channel_counts, overlay_meta = _resolve_unit_channel_counts(
            unit_data=unit_data,
            n_channels=cp.shape[0],
            unit_filter_source=unit_filter_source,
            unit_filter_values=unit_filter_values,
            max_channel_col=max_channel_col,
        )
        if not unit_channel_counts.empty:
            overlay_idx = unit_channel_counts.index.to_numpy(dtype=int)
            overlay_counts = unit_channel_counts.to_numpy(dtype=float)
            overlay_sizes = 10.0 + 8.0 * np.sqrt(overlay_counts)
            overlay_label = f"Units ({overlay_meta['filter_source']})"
            if len(overlay_meta["filter_values"]) > 0:
                overlay_label = (
                    f"Units ({overlay_meta['filter_source']}: "
                    + ", ".join(map(str, overlay_meta["filter_values"]))
                    + ")"
                )
            ax.scatter(
                x_um[overlay_idx],
                depth_um[overlay_idx],
                s=overlay_sizes,
                facecolors="green",
                edgecolors="green",
                alpha=0.28,
                linewidths=0.5,
                label=overlay_label,
                zorder=4,
            )

    ax.axhline(float(roi_end_um), color="black", linewidth=1.2, linestyle="--", alpha=0.8)
    ax.set_title(f"{probe_letter} | tip_position='min_y' | true aspect", pad=18)
    ax.set_xlabel("x (um)")
    ax.set_ylabel("DEPTH (um)")
    ax.set_xlim(*x_limits)
    ax.set_ylim(*y_limits)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.2)

    right_ax = ax.twinx()
    channel_ticks = np.arange(0, cp.shape[0], 20, dtype=int)
    tick_table = (
        pd.DataFrame({"channel": channel_ticks, "depth": depth_um[channel_ticks]})
        .dropna(subset=["depth"])
        .sort_values(["depth", "channel"])
        .drop_duplicates(subset=["depth"], keep="first")
    )
    right_ax.set_ylim(ax.get_ylim())
    right_ax.set_yticks(tick_table["depth"].to_numpy(dtype=float))
    right_ax.set_yticklabels([str(int(ch)) for ch in tick_table["channel"].tolist()])
    right_ax.set_ylabel("Channel # (every 20)")
    right_ax.grid(False)

    fig.suptitle(f"Probe {probe_letter}: ROI + brain-region map (min_y, true aspect)", fontsize=12, y=0.985)

    handles, labels = ax.get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.955), ncol=2, frameon=False)

    fig.subplots_adjust(top=0.84, left=0.24, right=0.76)

    if save_dir is not None:
        save_path = _resolve_plot_save_path(
            save_dir=save_dir,
            function_name="plot_roi_channel_comparison_min_y_true_aspect",
            probe_letter=probe_letter,
            filename=f"{probe_letter}_miny_ta.png",
        )
        fig.savefig(save_path, dpi=300)
        print(f"Saved true-aspect min_y ROI/brain-region map for probe {probe_letter} to: {save_path}")
    if show_plt:
        plt.show()

    info["unit_channel_counts"] = unit_channel_counts.to_dict()
    info["unit_overlay_meta"] = overlay_meta
    return info


def compute_roi_labels(
    quality_metrics: Dict[str, Any],
    ks_dir: Path,
    roi_end_um: float,
    tip_position: str = "min_y",
    in_label: str = "IN_ROI",
    out_label: str = "OUT_ROI",
) -> np.ndarray:
    if "maxChannels" not in quality_metrics:
        raise KeyError(
            f"quality_metrics is missing required key 'maxChannels' for ROI labeling (ks_dir={str(ks_dir)})."
        )

    ephys_data = bc.load_ephys_data(str(ks_dir))
    channel_positions = ephys_data[6]
    shank_y = channel_positions[:, 1].astype(float)
    max_channels = np.asarray(quality_metrics["maxChannels"]).astype(int)

    if np.any(max_channels < 0) or np.any(max_channels >= len(channel_positions)):
        raise IndexError(
            f"Found maxChannels outside valid range [0, {len(channel_positions)}) for ks_dir={str(ks_dir)}"
        )

    unit_y = channel_positions[max_channels, 1].astype(float)
    dist_um = compute_tip_distance_um(unit_y, shank_y, tip_position=tip_position)
    return np.where(dist_um <= float(roi_end_um), in_label, out_label)
