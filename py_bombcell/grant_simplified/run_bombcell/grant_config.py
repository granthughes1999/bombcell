from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

PROBE_LETTERS = ["A", "B", "C", "D", "E", "F"]
DEFAULT_PROBE_STREAM_NAMES = {
    "A": "Neuropix-PXI-100.ProbeA",
    "B": "Neuropix-PXI-100.ProbeB-AP",
    "C": "Neuropix-PXI-100.ProbeC",
    "D": "Neuropix-PXI-100.ProbeD",
    "E": "Neuropix-PXI-100.ProbeE-AP",
    "F": "Neuropix-PXI-100.ProbeF-AP",
}
DEFAULT_PROBE_RECORDING_ROI = {probe: None for probe in PROBE_LETTERS}


def _as_path(value: str | Path) -> Path:
    return value if isinstance(value, Path) else Path(value)


def _deep_update(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in src.items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            _deep_update(dst[key], value)
        else:
            dst[key] = value
    return dst


def load_config(config_path: str | Path | None = None) -> Dict[str, Any]:
    if config_path is None:
        config_path = os.environ.get(
            "GRANT_SIMPLIFIED_BOMBCELL_CONFIG",
            Path(__file__).resolve().parents[1] / "config" / "recording_config.json",
        )

    config_path = _as_path(config_path)
    with config_path.open("r", encoding="utf-8") as f:
        raw: Dict[str, Any] = json.load(f)

    recording_name = raw.get("recording_name")
    recordings_root = raw.get("recordings_root")
    if not recording_name or not recordings_root:
        raise ValueError("Config must include non-empty 'recording_name' and 'recordings_root'.")

    recordings_root_path = _as_path(recordings_root)
    recording_root = recordings_root_path / recording_name

    stream_names = dict(DEFAULT_PROBE_STREAM_NAMES)
    stream_names.update(raw.get("probe_stream_names", {}))

    probe_recording_roi = dict(DEFAULT_PROBE_RECORDING_ROI)
    probe_recording_roi.update(raw.get("probe_recording_roi", {}))

    open_ephys_subpath = raw.get(
        "open_ephys_continuous_subpath", "Record Node 103/experiment1/recording1/continuous"
    )
    structure_oebin_subpath = raw.get(
        "structure_oebin_subpath", "Record Node 103/experiment1/recording1/structure.oebin"
    )

    continuous_root = recording_root / Path(open_ephys_subpath)
    structure_oebin = recording_root / Path(structure_oebin_subpath)

    probe_dirs = {probe: continuous_root / stream_names[probe] for probe in PROBE_LETTERS}
    continuous_dat_paths = {probe: probe_dirs[probe] / "continuous.dat" for probe in PROBE_LETTERS}
    probe_kilosort_dirs = {probe: probe_dirs[probe] / "kilosort4" for probe in PROBE_LETTERS}

    cfg: Dict[str, Any] = {
        "config_path": config_path,
        "recording_name": recording_name,
        "recording_root": recording_root,
        "structure_oebin": structure_oebin,
        "probe_recording_roi": probe_recording_roi,
        "probes_all": list(raw.get("probes_all", PROBE_LETTERS)),
        "probe_kilosort_dirs": probe_kilosort_dirs,
        "continuous_dat_paths": continuous_dat_paths,
        "probe_param_overrides": raw.get("probe_param_overrides", {}),
        "mode_param_overrides": raw.get("mode_param_overrides", {}),
    }

    return cfg


def get_probe_mode_overrides(cfg: Dict[str, Any], probe: str, mode: str) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}

    mode_cfg = cfg.get("mode_param_overrides", {}).get(mode, {})
    _deep_update(overrides, mode_cfg.get("all", {}))
    _deep_update(overrides, mode_cfg.get("probes", {}).get(probe, {}))

    probe_cfg = cfg.get("probe_param_overrides", {}).get(probe, {})
    _deep_update(overrides, probe_cfg.get("all_modes", {}))
    _deep_update(overrides, probe_cfg.get("modes", {}).get(mode, {}))

    return overrides
