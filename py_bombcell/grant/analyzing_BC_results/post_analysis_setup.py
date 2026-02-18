from __future__ import annotations

from pathlib import Path
import sys
from typing import Dict, Any

import numpy as np
import pandas as pd
import bombcell as bc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from grant_config import load_grant_config, notebook_runtime_context  # noqa: E402

Y_COORDINATE_INDEX = 1
CHANNEL_POSITIONS_INDEX = 6


def load_post_analysis_context(config_path: str | Path = "../configs/grant_recording_config.json") -> Dict[str, Any]:
    cfg = load_grant_config(config_path)
    ctx = notebook_runtime_context(cfg)
    for p in [
        ctx["DEFAULT_KS_STAGING_ROOT"],
        ctx["NP20_KS_STAGING_ROOT"],
        ctx["BOMBCELL_KS_SINGLEPROBE_STAGING_ROOT"],
        ctx["DEFAULT_EXPORT_ROOT"],
        ctx["NP20_EXPORT_ROOT"],
        ctx["SINGLE_EXPORT_ROOT"],
    ]:
        p.mkdir(parents=True, exist_ok=True)
    return ctx


def label_units_by_tip_distance(
    quality_metrics: pd.DataFrame | dict,
    ks_dir: str | Path,
    roi_end_um: float,
    tip_position: str = "min_y",
    in_label: str = "IN_ROI",
    out_label: str = "OUTSIDE_ROI",
) -> pd.DataFrame:
    """
    Label units as IN_ROI / OUTSIDE_ROI based on distance from probe tip.

    Parameters
    ----------
    quality_metrics
        Bombcell quality metrics table (DataFrame or dict-like with a `maxChannels` column).
    ks_dir
        Kilosort directory for the probe.
    roi_end_um
        ROI extent in microns from tip along the shank (e.g. 950 for tip→950um).
    tip_position
        Which end of shank to treat as tip: "min_y" or "max_y".
    in_label, out_label
        Labels to assign within/outside ROI.
    """
    qm_df = pd.DataFrame(quality_metrics).copy()
    if "maxChannels" not in qm_df.columns:
        raise KeyError("quality_metrics must include a 'maxChannels' column.")

    ephys_data = bc.load_ephys_data(str(ks_dir))  # tuple shape follows bc.load_ephys_data docs
    channel_positions = ephys_data[CHANNEL_POSITIONS_INDEX]
    shank_y = channel_positions[:, Y_COORDINATE_INDEX].astype(float)
    max_channels = qm_df["maxChannels"].astype(int).to_numpy()
    if np.any(max_channels < 0) or np.any(max_channels >= len(channel_positions)):
        raise IndexError(
            f"Found maxChannels outside valid range [0, {len(channel_positions) - 1}] for ks_dir={ks_dir}"
        )
    unit_y = channel_positions[max_channels, Y_COORDINATE_INDEX].astype(float)

    if tip_position == "min_y":
        tip_y = float(np.nanmin(shank_y))
        dist_um = unit_y - tip_y
    elif tip_position == "max_y":
        tip_y = float(np.nanmax(shank_y))
        dist_um = tip_y - unit_y
    else:
        raise ValueError("tip_position must be 'min_y' or 'max_y'.")

    qm_df["distance_from_tip_um"] = dist_um
    qm_df["roi_label"] = np.where(qm_df["distance_from_tip_um"] <= float(roi_end_um), in_label, out_label)
    return qm_df
