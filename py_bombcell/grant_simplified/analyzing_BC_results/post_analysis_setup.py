from __future__ import annotations

from pathlib import Path
import sys
from typing import Dict, Any

import numpy as np
import pandas as pd
import bombcell as bc

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run_bombcell"))
from grant_config import load_config  # noqa: E402


def load_post_analysis_context(config_path: str | Path = "../config/recording_config.json") -> Dict[str, Any]:
    cfg = load_config(config_path)
    return {
        "RECORDING_ROOT": cfg["recording_root"],
        "PROBES_ALL": cfg["probes_all"],
        "KILOSORT_DIRS": cfg["probe_kilosort_dirs"],
        "PROBE_RECORDING_ROI": cfg["probe_recording_roi"],
    }


def label_units_by_tip_distance(
    quality_metrics: pd.DataFrame | dict,
    ks_dir: str | Path,
    roi_end_um: float,
    tip_position: str = "min_y",
    in_label: str = "IN_ROI",
    out_label: str = "OUT_ROI",
) -> pd.DataFrame:
    qm_df = pd.DataFrame(quality_metrics).copy()
    if "maxChannels" not in qm_df.columns:
        raise KeyError("quality_metrics must include a 'maxChannels' column.")

    channel_positions = bc.load_ephys_data(str(ks_dir))[6]
    shank_y = channel_positions[:, 1].astype(float)
    max_channels = qm_df["maxChannels"].astype(int).to_numpy()
    if np.any(max_channels < 0) or np.any(max_channels >= len(channel_positions)):
        raise IndexError(
            f"Found maxChannels outside valid range [0, {len(channel_positions) - 1}] for ks_dir={ks_dir}"
        )
    unit_y = channel_positions[max_channels, 1].astype(float)

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
