from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

PROBE_LETTERS = ["A", "B", "C", "D", "E", "F"]
DEFAULT_NP20_PROBES = ["A", "C", "D"]
DEFAULT_PROBE_STREAM_NAMES = {
    "A": "Neuropix-PXI-100.ProbeA",
    "B": "Neuropix-PXI-100.ProbeB-AP",
    "C": "Neuropix-PXI-100.ProbeC",
    "D": "Neuropix-PXI-100.ProbeD",
    "E": "Neuropix-PXI-100.ProbeE-AP",
    "F": "Neuropix-PXI-100.ProbeF-AP",
}
DEFAULT_PROBE_BRAIN_REGIONS = {
    "A": "NP2.0 Simplex Lobule & Interposed Nucleus",
    "B": "NP1.0 Pontine Nuclei",
    "C": "NP2.0 Motor Cortex",
    "D": "NP2.0 Ventral Anterior Lateral complex of the thalamus",
    "E": "NP1.0 Substantia Nigra (SNR)",
    "F": "NP1.0 Reticular Nucleus"
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


def load_grant_config(config_path: str | Path | None = None) -> Dict[str, Any]:
    if config_path is None:
        config_path = os.environ.get(
            "GRANT_BOMBCELL_CONFIG",
            Path(__file__).resolve().parent / "configs" / "grant_recording_config.json",
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

    probe_regions = dict(DEFAULT_PROBE_BRAIN_REGIONS)
    probe_regions.update(raw.get("probe_brain_regions", {}))
    probe_recording_roi = dict(DEFAULT_PROBE_RECORDING_ROI)
    probe_recording_roi.update(raw.get("probe_recording_roi", {}))

    np20_probes = raw.get("np20_probes", DEFAULT_NP20_PROBES)
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

    bombcell_default_root = recording_root / "bombcell" / "bombcell_DEFAULT"
    bombcell_np20_root = recording_root / "bombcell" / "bombcell_NP2.0"
    bombcell_singleprobe_root = recording_root / "bombcell" / "bombcell_single_probe"

    cfg: Dict[str, Any] = {
        "config_path": config_path,
        "recording_name": recording_name,
        "recordings_root": recordings_root_path,
        "recording_root": recording_root,
        "continuous_root": continuous_root,
        "structure_oebin": structure_oebin,
        "probe_stream_names": stream_names,
        "probes_all": list(PROBE_LETTERS),
        "np20_probes": list(np20_probes),
        "probe_regions": probe_regions,
        "probe_recording_roi": probe_recording_roi,
        "probe_dirs": probe_dirs,
        "continuous_dat_paths": continuous_dat_paths,
        "probe_kilosort_dirs": probe_kilosort_dirs,
        "bombcell_default_root": bombcell_default_root,
        "bombcell_np20_root": bombcell_np20_root,
        "bombcell_singleprobe_root": bombcell_singleprobe_root,
        "default_ks_staging_root": bombcell_default_root,
        "np20_ks_staging_root": bombcell_np20_root,
        "default_export_root": bombcell_default_root / "batch_DEFAULT_results",
        "np20_export_root": bombcell_np20_root / "NP2_ReRun_results",
        "single_export_root": bombcell_singleprobe_root / "single_probe_results",
        "probe_param_overrides": raw.get("probe_param_overrides", {}),
        "mode_param_overrides": raw.get("mode_param_overrides", {}),
        "custom_channel_map_notes": raw.get("custom_channel_map_notes", ""),
    }

    return cfg


def notebook_runtime_context(cfg: Dict[str, Any]) -> Dict[str, Any]:
    context: Dict[str, Any] = {
        "NP_recording_name": cfg["recording_name"],
        "RECORDING_ROOT": cfg["recording_root"],
        "BOMBCELL_DEFAULT_ROOT": cfg["bombcell_default_root"],
        "BOMBCELL_NP20_ROOT": cfg["bombcell_np20_root"],
        "BOMBCELL_SINGLEPROBE_ROOT": cfg["bombcell_singleprobe_root"],
        "DEFAULT_KS_STAGING_ROOT": cfg["default_ks_staging_root"],
        "NP20_KS_STAGING_ROOT": cfg["np20_ks_staging_root"],
        "BOMBCELL_KS_SINGLEPROBE_STAGING_ROOT": cfg["bombcell_singleprobe_root"],
        "DEFAULT_EXPORT_ROOT": cfg["default_export_root"],
        "NP20_EXPORT_ROOT": cfg["np20_export_root"],
        "SINGLE_EXPORT_ROOT": cfg["single_export_root"],
        "PROBES_ALL": cfg["probes_all"],
        "PROBES_NP20": cfg["np20_probes"],
        "PROBE_BRAIN_REGIONS": cfg["probe_regions"],
        "PROBE_RECORDING_ROI": cfg["probe_recording_roi"],
        "PROBE_DIRS": cfg["probe_dirs"],
        "CONTINUOUS_DAT_PATHS": cfg["continuous_dat_paths"],
        "KILOSORT_DIRS": cfg["probe_kilosort_dirs"],
        "STRUCTURE_OEBIN": cfg["structure_oebin"],
    }

    for p in PROBE_LETTERS:
        context[f"probe{p}_Dir"] = str(cfg["probe_dirs"][p])
        context[f"probe{p}_continousDir"] = str(cfg["continuous_dat_paths"][p])
        context[f"probe{p}_continuousDir"] = str(cfg["continuous_dat_paths"][p])
        context[f"probe{p}_kilosort4Dir"] = str(cfg["probe_kilosort_dirs"][p])

    context["continousDir"] = [str(cfg["continuous_dat_paths"][p]) for p in PROBE_LETTERS]
    context["continuousDir"] = [str(cfg["continuous_dat_paths"][p]) for p in PROBE_LETTERS]
    context["kilosort_Dirs"] = [str(cfg["probe_kilosort_dirs"][p]) for p in PROBE_LETTERS]
    context["probeLetters"] = list(PROBE_LETTERS)
    context["structur_oebin"] = str(cfg["structure_oebin"])
    return context


def get_probe_mode_overrides(cfg: Dict[str, Any], probe: str, mode: str) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}

    mode_cfg = cfg.get("mode_param_overrides", {}).get(mode, {})
    _deep_update(overrides, mode_cfg.get("all", {}))
    _deep_update(overrides, mode_cfg.get("probes", {}).get(probe, {}))

    probe_cfg = cfg.get("probe_param_overrides", {}).get(probe, {})
    _deep_update(overrides, probe_cfg.get("all_modes", {}))
    _deep_update(overrides, probe_cfg.get("modes", {}).get(mode, {}))

    return overrides
