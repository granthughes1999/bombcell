from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import bombcell as bc

from mice.Reach15.helper_func.nwb_data_prep import choose_event_time_col


ARTIFACT_ONLY_RULE_DEFAULTS: dict[str, float] = {
    "min_spikes_per_unit": 5,
    "min_pulse_hit_rate": 0.80,
    "min_fraction_spikes_locked": 0.90,
    "min_mean_trial_pulse_fraction": 0.80,
    "max_off_pulse_fraction": 0.10,
    "max_median_latency_ms": 1.00,
    "max_latency_jitter_ms": 0.20,
    "max_pre_to_post_ratio": 0.20,
}


def _coerce_1d_float_array(values: Any) -> np.ndarray:
    arr = np.asarray(values)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    return arr.astype(float).ravel()


def _normalize_cluster_ids(values: Any) -> np.ndarray:
    series = pd.Series(np.asarray(values).ravel())
    series = pd.to_numeric(series, errors="coerce").dropna().astype(int)
    return series.to_numpy()


def _load_tabular_source(path: Path) -> Any:
    suffix = path.suffix.lower()
    if suffix == ".npy":
        return np.load(path, allow_pickle=True)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".tsv":
        return pd.read_csv(path, sep="\t")
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix in {".pkl", ".pickle"}:
        return pd.read_pickle(path)
    raise ValueError(f"Unsupported event-source file type: {path.suffix}")


def _extract_start_times_from_object(
    obj: Any,
    *,
    time_col: str | None = None,
    stimulus_filter: str | None = None,
) -> np.ndarray:
    if isinstance(obj, pd.DataFrame):
        df = obj.copy()
        if stimulus_filter is not None and "stimulus" in df.columns:
            df = df[df["stimulus"].astype(str) == str(stimulus_filter)].copy()
        event_time_col = time_col or choose_event_time_col(df)
        values = pd.to_numeric(df[event_time_col], errors="coerce").dropna().to_numpy(dtype=float)
        return values

    if isinstance(obj, pd.Series):
        return pd.to_numeric(obj, errors="coerce").dropna().to_numpy(dtype=float)

    if isinstance(obj, dict):
        for key in ("stim_df", "df_stim", "events", "event_df"):
            if key in obj and isinstance(obj[key], pd.DataFrame):
                return _extract_start_times_from_object(
                    obj[key],
                    time_col=time_col,
                    stimulus_filter=stimulus_filter,
                )
        for key in ("start_times", "event_start_times", "start_time", "times"):
            if key in obj:
                return _coerce_1d_float_array(obj[key])
        raise ValueError(
            "Could not find an event table or start-time vector in the loaded object."
        )

    return _coerce_1d_float_array(obj)


def load_event_start_times(
    event_source: str | Path | pd.DataFrame | pd.Series | np.ndarray | list[float] | tuple[float, ...] | dict[str, Any],
    *,
    time_col: str | None = None,
    stimulus_filter: str | None = None,
    times_are_samples: bool = False,
    sample_rate_hz: float | None = None,
    sort_values: bool = True,
    unique_only: bool = True,
) -> np.ndarray:
    """
    Load aligned event start times from a vector or tabular source.

    Supported file types: .npy, .csv, .tsv, .parquet, .pkl, .pickle.
    """
    if isinstance(event_source, (str, Path)):
        source_path = Path(event_source)
        if not source_path.exists():
            raise FileNotFoundError(f"Event source not found: {source_path}")
        loaded = _load_tabular_source(source_path)
    else:
        loaded = event_source

    start_times = _extract_start_times_from_object(
        loaded,
        time_col=time_col,
        stimulus_filter=stimulus_filter,
    )

    if times_are_samples:
        if sample_rate_hz is None:
            raise ValueError("sample_rate_hz is required when times_are_samples=True.")
        start_times = start_times / float(sample_rate_hz)

    start_times = start_times[np.isfinite(start_times)]
    if unique_only:
        start_times = np.unique(start_times)
    if sort_values:
        start_times = np.sort(start_times)
    return start_times.astype(float)


def build_pulse_table(
    event_start_times_s: np.ndarray | list[float],
    *,
    pulse_count: int = 10,
    inter_pulse_interval_s: float = 0.010,
) -> pd.DataFrame:
    if pulse_count <= 0:
        raise ValueError("pulse_count must be positive.")

    event_start_times_s = _coerce_1d_float_array(event_start_times_s)
    event_start_times_s = event_start_times_s[np.isfinite(event_start_times_s)]
    event_start_times_s = np.sort(event_start_times_s)
    if event_start_times_s.size == 0:
        raise ValueError("No valid event start times were provided.")

    pulse_offsets_s = np.arange(pulse_count, dtype=float) * float(inter_pulse_interval_s)
    pulse_times_s = event_start_times_s[:, None] + pulse_offsets_s[None, :]

    pulse_table = pd.DataFrame(
        {
            "trial_index": np.repeat(np.arange(event_start_times_s.size, dtype=int), pulse_count),
            "pulse_index": np.tile(np.arange(pulse_count, dtype=int), event_start_times_s.size),
            "event_start_time_s": np.repeat(event_start_times_s, pulse_count),
            "pulse_offset_s": np.tile(pulse_offsets_s, event_start_times_s.size),
            "pulse_time_s": pulse_times_s.reshape(-1),
        }
    )
    return pulse_table


def extract_stimulus_start_times(
    stim_df: pd.DataFrame,
    stimulus: str | list[str] | tuple[str, ...],
    *,
    time_col: str | None = None,
    unique_only: bool = True,
    sort_values: bool = True,
) -> np.ndarray:
    if "stimulus" not in stim_df.columns:
        raise ValueError("stim_df must contain a 'stimulus' column.")

    stimuli = [str(stimulus)] if isinstance(stimulus, str) else [str(s) for s in stimulus]
    event_time_col = time_col or choose_event_time_col(stim_df)
    times = pd.to_numeric(
        stim_df.loc[stim_df["stimulus"].astype(str).isin(stimuli), event_time_col],
        errors="coerce",
    ).dropna().to_numpy(dtype=float)

    if unique_only:
        times = np.unique(times)
    if sort_values:
        times = np.sort(times)
    return times.astype(float)


def collapse_train_seed_times(
    candidate_start_times_s: np.ndarray | list[float],
    *,
    gap_s: float = 1.0,
) -> np.ndarray:
    if gap_s <= 0:
        raise ValueError("gap_s must be positive.")

    candidate_start_times_s = _coerce_1d_float_array(candidate_start_times_s)
    candidate_start_times_s = candidate_start_times_s[np.isfinite(candidate_start_times_s)]
    candidate_start_times_s = np.sort(candidate_start_times_s)
    if candidate_start_times_s.size == 0:
        return np.array([], dtype=float)

    grouped = [float(candidate_start_times_s[0])]
    for start_time_s in candidate_start_times_s[1:]:
        if float(start_time_s) - float(grouped[-1]) > float(gap_s):
            grouped.append(float(start_time_s))
    return np.asarray(grouped, dtype=float)


def build_observed_pulse_table(
    pulse_times_s: np.ndarray | list[float],
    candidate_start_times_s: np.ndarray | list[float],
    *,
    look_ahead_s: float = 1.0,
    min_pulses_per_train: int = 1,
) -> pd.DataFrame:
    if look_ahead_s <= 0:
        raise ValueError("look_ahead_s must be positive.")
    if min_pulses_per_train <= 0:
        raise ValueError("min_pulses_per_train must be positive.")

    pulse_times_s = _coerce_1d_float_array(pulse_times_s)
    pulse_times_s = pulse_times_s[np.isfinite(pulse_times_s)]
    pulse_times_s = np.sort(np.unique(pulse_times_s))
    if pulse_times_s.size == 0:
        raise ValueError("No pulse times were provided.")

    train_seed_times_s = collapse_train_seed_times(candidate_start_times_s, gap_s=look_ahead_s)
    rows: list[dict[str, float | int]] = []
    trial_index = 0

    for seed_time_s in train_seed_times_s:
        in_window = pulse_times_s[
            (pulse_times_s >= float(seed_time_s)) &
            (pulse_times_s <= float(seed_time_s) + float(look_ahead_s))
        ]
        if in_window.size < min_pulses_per_train:
            continue

        event_start_time_s = float(in_window[0])
        for pulse_index, pulse_time_s in enumerate(in_window):
            rows.append(
                {
                    "trial_index": int(trial_index),
                    "pulse_index": int(pulse_index),
                    "event_start_time_s": event_start_time_s,
                    "pulse_offset_s": float(pulse_time_s - event_start_time_s),
                    "pulse_time_s": float(pulse_time_s),
                    "train_seed_time_s": float(seed_time_s),
                }
            )
        trial_index += 1

    if not rows:
        return pd.DataFrame(
            columns=[
                "trial_index",
                "pulse_index",
                "event_start_time_s",
                "pulse_offset_s",
                "pulse_time_s",
                "train_seed_time_s",
            ]
        )

    return pd.DataFrame(rows)


def build_pulse_table_from_stim_df(
    stim_df: pd.DataFrame,
    *,
    start_stimuli: tuple[str, ...] = (
        "stimulation_reachInit_stimROI_start_times",
        "opto_tagging_timestamps",
    ),
    pulse_stimulus: str = "optical_timestamps",
    fallback_pulse_stimulus: str | None = "opto_tagging_timestamps",
    look_ahead_s: float = 1.0,
    min_pulses_per_train: int = 1,
    time_col: str | None = None,
) -> dict[str, Any]:
    candidate_start_times_s = extract_stimulus_start_times(
        stim_df,
        start_stimuli,
        time_col=time_col,
    )
    if candidate_start_times_s.size == 0:
        raise ValueError(
            "No candidate train starts were found for "
            f"start_stimuli={list(start_stimuli)}."
        )

    pulse_source_stimulus = str(pulse_stimulus)
    pulse_times_s = extract_stimulus_start_times(
        stim_df,
        pulse_source_stimulus,
        time_col=time_col,
    )
    if pulse_times_s.size == 0 and fallback_pulse_stimulus is not None:
        pulse_source_stimulus = str(fallback_pulse_stimulus)
        pulse_times_s = extract_stimulus_start_times(
            stim_df,
            pulse_source_stimulus,
            time_col=time_col,
        )

    if pulse_times_s.size == 0:
        raise ValueError(
            "No pulse timestamps were found for "
            f"pulse_stimulus='{pulse_stimulus}'"
            + (
                f" or fallback_pulse_stimulus='{fallback_pulse_stimulus}'."
                if fallback_pulse_stimulus is not None else "."
            )
        )

    train_seed_times_s = collapse_train_seed_times(candidate_start_times_s, gap_s=look_ahead_s)
    pulse_table = build_observed_pulse_table(
        pulse_times_s,
        train_seed_times_s,
        look_ahead_s=look_ahead_s,
        min_pulses_per_train=min_pulses_per_train,
    )
    if pulse_table.empty:
        raise ValueError(
            "No pulse trains were found within the requested look-ahead window. "
            f"start_stimuli={list(start_stimuli)}, pulse_stimulus='{pulse_source_stimulus}', "
            f"look_ahead_s={look_ahead_s}."
        )

    pulse_train_start_times = (
        pulse_table[["trial_index", "event_start_time_s"]]
        .drop_duplicates(subset=["trial_index"])
        ["event_start_time_s"]
        .to_numpy(dtype=float)
    )

    return {
        "pulse_table": pulse_table,
        "pulse_train_start_times": pulse_train_start_times,
        "candidate_start_times_s": candidate_start_times_s,
        "train_seed_times_s": train_seed_times_s,
        "pulse_times_s": pulse_times_s,
        "pulse_source_stimulus": pulse_source_stimulus,
        "start_stimuli": tuple(str(s) for s in start_stimuli),
        "time_col": time_col or choose_event_time_col(stim_df),
    }


def extract_cluster_spike_times_s(
    spike_times_samples: np.ndarray,
    spike_clusters: np.ndarray,
    cluster_id: int,
    sample_rate_hz: float,
) -> np.ndarray:
    mask = np.asarray(spike_clusters).astype(int) == int(cluster_id)
    if not np.any(mask):
        return np.array([], dtype=float)
    return np.asarray(spike_times_samples, dtype=float)[mask] / float(sample_rate_hz)


def _load_optional_cluster_tsv(ks_dir: Path, filename: str) -> pd.DataFrame | None:
    path = ks_dir / filename
    if not path.exists():
        return None
    return pd.read_csv(path, sep="\t")


def _resolve_qm_cluster_ids(ks_dir: Path, param: dict[str, Any], qm_df: pd.DataFrame) -> np.ndarray:
    unique_templates = _normalize_cluster_ids(param.get("unique_templates", []))
    if unique_templates.size == len(qm_df):
        return unique_templates

    unit_type_df = _load_optional_cluster_tsv(ks_dir, "cluster_bc_unitType.tsv")
    if unit_type_df is not None and "cluster_id" in unit_type_df.columns:
        fallback_ids = _normalize_cluster_ids(unit_type_df["cluster_id"].to_numpy())
        if fallback_ids.size == len(qm_df):
            return fallback_ids

    raise ValueError(
        "Could not align Bombcell quality-metric rows with cluster ids. "
        f"quality_metrics rows={len(qm_df)}, unique_templates={unique_templates.size}."
    )


def load_probe_artifact_context(
    ks_dir: str | Path,
    *,
    save_path: str | Path | None = None,
    sample_rate_hz: float | None = None,
) -> dict[str, Any]:
    ks_dir = Path(ks_dir)
    save_path = Path(save_path) if save_path is not None else ks_dir / "bombcell"

    spike_times_path = ks_dir / "spike_times_corrected.npy"
    if not spike_times_path.exists():
        spike_times_path = ks_dir / "spike_times.npy"

    spike_clusters_path = ks_dir / "spike_clusters.npy"
    if not spike_clusters_path.exists():
        spike_clusters_path = ks_dir / "spike_templates.npy"

    if not spike_times_path.exists():
        raise FileNotFoundError(f"Spike-times file not found under {ks_dir}")
    if not spike_clusters_path.exists():
        raise FileNotFoundError(f"Spike-clusters file not found under {ks_dir}")
    if not save_path.exists():
        raise FileNotFoundError(f"Bombcell save path not found: {save_path}")

    spike_times_samples = np.load(spike_times_path).squeeze().astype(np.int64)
    spike_clusters = np.load(spike_clusters_path).squeeze().astype(int)

    param, quality_metrics, _ = bc.load_bc_results(str(save_path))
    if param is None:
        raise FileNotFoundError(f"Bombcell parameter file not found in {save_path}")
    if quality_metrics is None:
        raise FileNotFoundError(f"Bombcell quality-metrics file not found in {save_path}")

    qm_df = quality_metrics.copy() if isinstance(quality_metrics, pd.DataFrame) else pd.DataFrame(quality_metrics)
    qm_cluster_ids = _resolve_qm_cluster_ids(ks_dir, param, qm_df)
    qm_df = qm_df.copy()
    qm_df.insert(0, "cluster_id", qm_cluster_ids.astype(int))

    unit_type_df = _load_optional_cluster_tsv(ks_dir, "cluster_bc_unitType.tsv")
    if unit_type_df is not None and "cluster_id" in unit_type_df.columns:
        value_col = "bc_unitType" if "bc_unitType" in unit_type_df.columns else None
        if value_col is not None:
            unit_type_clean = unit_type_df[["cluster_id", value_col]].copy()
            unit_type_clean["cluster_id"] = pd.to_numeric(
                unit_type_clean["cluster_id"], errors="coerce"
            )
            unit_type_clean = unit_type_clean.dropna(subset=["cluster_id"])
            unit_type_clean["cluster_id"] = unit_type_clean["cluster_id"].astype(int)
            qm_df = qm_df.merge(unit_type_clean, on="cluster_id", how="left")

    if "bc_unitType" not in qm_df.columns:
        _, unit_type_string = bc.get_quality_unit_type(param, qm_df)
        qm_df["bc_unitType"] = unit_type_string

    reason_df = _load_optional_cluster_tsv(ks_dir, "cluster_bc_classificationReason.tsv")
    if reason_df is not None and "cluster_id" in reason_df.columns:
        reason_col = "bc_classificationReason" if "bc_classificationReason" in reason_df.columns else None
        if reason_col is not None:
            reason_clean = reason_df[["cluster_id", reason_col]].copy()
            reason_clean["cluster_id"] = pd.to_numeric(
                reason_clean["cluster_id"], errors="coerce"
            )
            reason_clean = reason_clean.dropna(subset=["cluster_id"])
            reason_clean["cluster_id"] = reason_clean["cluster_id"].astype(int)
            qm_df = qm_df.merge(reason_clean, on="cluster_id", how="left")

    resolved_sample_rate_hz = float(sample_rate_hz or param.get("ephys_sample_rate") or 30000.0)

    return {
        "ks_dir": ks_dir,
        "save_path": save_path,
        "param": param,
        "quality_metrics_df": qm_df,
        "cluster_ids": qm_df["cluster_id"].astype(int).to_numpy(),
        "sample_rate_hz": resolved_sample_rate_hz,
        "spike_times_samples": spike_times_samples,
        "spike_clusters": spike_clusters,
        "recording_duration_s": float(np.max(spike_times_samples) / resolved_sample_rate_hz)
        if spike_times_samples.size
        else np.nan,
    }


def compute_opto_artifact_metrics(
    *,
    spike_times_samples: np.ndarray,
    spike_clusters: np.ndarray,
    cluster_ids: np.ndarray | list[int],
    sample_rate_hz: float,
    pulse_table: pd.DataFrame,
    post_pulse_window_s: float = 0.001,
    pre_pulse_window_s: float = 0.001,
    recording_duration_s: float | None = None,
) -> pd.DataFrame:
    required_columns = {"trial_index", "pulse_index", "pulse_time_s"}
    missing = required_columns - set(pulse_table.columns)
    if missing:
        raise KeyError(f"pulse_table is missing required columns: {sorted(missing)}")

    if post_pulse_window_s <= 0:
        raise ValueError("post_pulse_window_s must be positive.")
    if pre_pulse_window_s < 0:
        raise ValueError("pre_pulse_window_s cannot be negative.")

    cluster_ids = _normalize_cluster_ids(cluster_ids)
    if cluster_ids.size == 0:
        raise ValueError("No cluster ids were provided.")

    pulse_table = pulse_table.sort_values(["trial_index", "pulse_index", "pulse_time_s"]).reset_index(drop=True)
    pulse_times_s = pulse_table["pulse_time_s"].to_numpy(dtype=float)
    trial_codes = pd.factorize(pulse_table["trial_index"])[0]
    n_trials = int(trial_codes.max()) + 1 if trial_codes.size else 0
    n_pulses = int(pulse_times_s.size)

    order = np.argsort(spike_clusters, kind="mergesort")
    sorted_clusters = np.asarray(spike_clusters, dtype=int)[order]
    sorted_spike_times_s = np.asarray(spike_times_samples, dtype=float)[order] / float(sample_rate_hz)

    cluster_starts = np.searchsorted(sorted_clusters, cluster_ids, side="left")
    cluster_stops = np.searchsorted(sorted_clusters, cluster_ids, side="right")

    resolved_recording_duration_s = float(recording_duration_s) if recording_duration_s is not None else (
        float(np.max(spike_times_samples) / float(sample_rate_hz)) if np.asarray(spike_times_samples).size else np.nan
    )
    total_locked_window_s = float(n_pulses) * float(post_pulse_window_s)
    off_pulse_time_s = (
        max(float(resolved_recording_duration_s) - total_locked_window_s, 0.0)
        if np.isfinite(resolved_recording_duration_s)
        else np.nan
    )

    rows: list[dict[str, Any]] = []
    for cluster_id, start_idx, stop_idx in zip(cluster_ids, cluster_starts, cluster_stops):
        cluster_spike_times_s = sorted_spike_times_s[start_idx:stop_idx]
        total_spikes = int(cluster_spike_times_s.size)

        if total_spikes == 0:
            rows.append(
                {
                    "cluster_id": int(cluster_id),
                    "nSpikes_total": 0,
                    "nPulses_total": n_pulses,
                    "nTrials_total": n_trials,
                    "nPulseHits": 0,
                    "pulse_hit_rate": 0.0,
                    "fraction_spikes_locked": 0.0,
                    "off_pulse_spikes": 0,
                    "off_pulse_fraction": 0.0,
                    "spikes_in_pre_window": 0,
                    "spikes_in_post_window": 0,
                    "pre_to_post_ratio": np.nan,
                    "median_latency_ms": np.nan,
                    "mean_latency_ms": np.nan,
                    "latency_jitter_ms": np.nan,
                    "mean_trial_pulse_fraction": 0.0,
                    "full_train_trial_fraction": 0.0,
                    "off_pulse_rate_hz": np.nan,
                    "mean_post_spikes_per_hit": np.nan,
                }
            )
            continue

        post_left = np.searchsorted(cluster_spike_times_s, pulse_times_s, side="left")
        post_right = np.searchsorted(cluster_spike_times_s, pulse_times_s + float(post_pulse_window_s), side="left")
        post_counts = post_right - post_left
        hit_mask = post_counts > 0

        first_latency_s = np.full(n_pulses, np.nan, dtype=float)
        valid_hits = hit_mask & (post_left < cluster_spike_times_s.size)
        first_latency_s[valid_hits] = cluster_spike_times_s[post_left[valid_hits]] - pulse_times_s[valid_hits]
        latency_ms = first_latency_s[hit_mask] * 1000.0

        pre_left = np.searchsorted(cluster_spike_times_s, pulse_times_s - float(pre_pulse_window_s), side="left")
        pre_right = np.searchsorted(cluster_spike_times_s, pulse_times_s, side="left")
        pre_counts = pre_right - pre_left

        prev_pulse_idx = np.searchsorted(pulse_times_s, cluster_spike_times_s, side="right") - 1
        valid_prev = prev_pulse_idx >= 0
        delta_s = np.full(total_spikes, np.inf, dtype=float)
        delta_s[valid_prev] = cluster_spike_times_s[valid_prev] - pulse_times_s[prev_pulse_idx[valid_prev]]
        spike_in_post = valid_prev & (delta_s >= 0.0) & (delta_s < float(post_pulse_window_s))

        spikes_in_post_window = int(spike_in_post.sum())
        spikes_in_pre_window = int(pre_counts.sum())
        off_pulse_spikes = int(total_spikes - spikes_in_post_window)

        trial_hit_fraction = np.zeros(n_trials, dtype=float)
        for trial_idx in range(n_trials):
            trial_mask = trial_codes == trial_idx
            trial_hit_fraction[trial_idx] = float(hit_mask[trial_mask].mean()) if np.any(trial_mask) else np.nan

        fraction_spikes_locked = float(spikes_in_post_window / total_spikes)
        off_pulse_fraction = float(off_pulse_spikes / total_spikes)
        pre_to_post_ratio = float(spikes_in_pre_window / spikes_in_post_window) if spikes_in_post_window else np.nan

        rows.append(
            {
                "cluster_id": int(cluster_id),
                "nSpikes_total": total_spikes,
                "nPulses_total": n_pulses,
                "nTrials_total": n_trials,
                "nPulseHits": int(hit_mask.sum()),
                "pulse_hit_rate": float(hit_mask.mean()),
                "fraction_spikes_locked": fraction_spikes_locked,
                "off_pulse_spikes": off_pulse_spikes,
                "off_pulse_fraction": off_pulse_fraction,
                "spikes_in_pre_window": spikes_in_pre_window,
                "spikes_in_post_window": spikes_in_post_window,
                "pre_to_post_ratio": pre_to_post_ratio,
                "median_latency_ms": float(np.nanmedian(latency_ms)) if latency_ms.size else np.nan,
                "mean_latency_ms": float(np.nanmean(latency_ms)) if latency_ms.size else np.nan,
                "latency_jitter_ms": float(np.nanstd(latency_ms)) if latency_ms.size else np.nan,
                "mean_trial_pulse_fraction": float(np.nanmean(trial_hit_fraction)) if trial_hit_fraction.size else np.nan,
                "full_train_trial_fraction": float(np.mean(trial_hit_fraction == 1.0)) if trial_hit_fraction.size else 0.0,
                "off_pulse_rate_hz": float(off_pulse_spikes / off_pulse_time_s)
                if np.isfinite(off_pulse_time_s) and off_pulse_time_s > 0
                else np.nan,
                "mean_post_spikes_per_hit": float(np.nanmean(post_counts[hit_mask])) if np.any(hit_mask) else np.nan,
            }
        )

    return pd.DataFrame(rows).sort_values("cluster_id").reset_index(drop=True)


def apply_artifact_only_rules(
    metrics_df: pd.DataFrame,
    **threshold_overrides: float,
) -> pd.DataFrame:
    thresholds = dict(ARTIFACT_ONLY_RULE_DEFAULTS)
    thresholds.update(threshold_overrides)

    out = metrics_df.copy()
    min_spikes = float(thresholds["min_spikes_per_unit"])

    pass_map = {
        "nSpikes_total>=min_spikes_per_unit": out["nSpikes_total"].fillna(0) >= min_spikes,
        "pulse_hit_rate>=min_pulse_hit_rate": out["pulse_hit_rate"].fillna(0) >= float(thresholds["min_pulse_hit_rate"]),
        "fraction_spikes_locked>=min_fraction_spikes_locked": out["fraction_spikes_locked"].fillna(0)
        >= float(thresholds["min_fraction_spikes_locked"]),
        "mean_trial_pulse_fraction>=min_mean_trial_pulse_fraction": out["mean_trial_pulse_fraction"].fillna(0)
        >= float(thresholds["min_mean_trial_pulse_fraction"]),
        "off_pulse_fraction<=max_off_pulse_fraction": out["off_pulse_fraction"].fillna(1)
        <= float(thresholds["max_off_pulse_fraction"]),
        "median_latency_ms<=max_median_latency_ms": out["median_latency_ms"].fillna(np.inf)
        <= float(thresholds["max_median_latency_ms"]),
        "latency_jitter_ms<=max_latency_jitter_ms": out["latency_jitter_ms"].fillna(np.inf)
        <= float(thresholds["max_latency_jitter_ms"]),
        "pre_to_post_ratio<=max_pre_to_post_ratio": out["pre_to_post_ratio"].fillna(np.inf)
        <= float(thresholds["max_pre_to_post_ratio"]),
    }

    pass_df = pd.DataFrame(pass_map)
    out["artifact_rule_pass_count"] = pass_df.sum(axis=1).astype(int)
    out["artifact_rule_total"] = int(pass_df.shape[1])
    out["artifact_only_candidate"] = pass_df.all(axis=1)

    normalized_jitter = 1.0 - (
        out["latency_jitter_ms"].fillna(np.inf) / max(float(thresholds["max_latency_jitter_ms"]) * 2.0, 1e-9)
    )
    normalized_latency = 1.0 - (
        out["median_latency_ms"].fillna(np.inf) / max(float(thresholds["max_median_latency_ms"]) * 2.0, 1e-9)
    )
    out["artifact_score"] = (
        0.35 * out["pulse_hit_rate"].fillna(0.0)
        + 0.35 * out["fraction_spikes_locked"].fillna(0.0)
        + 0.15 * out["mean_trial_pulse_fraction"].fillna(0.0)
        + 0.10 * np.clip(normalized_latency, 0.0, 1.0)
        + 0.05 * np.clip(normalized_jitter, 0.0, 1.0)
    )

    pass_strings: list[str] = []
    fail_strings: list[str] = []
    summary_strings: list[str] = []
    for idx in range(len(out)):
        passed = [name for name, values in pass_map.items() if bool(values.iloc[idx])]
        failed = [name for name, values in pass_map.items() if not bool(values.iloc[idx])]
        pass_strings.append(" | ".join(passed))
        fail_strings.append(" | ".join(failed))
        if out.iloc[idx]["artifact_only_candidate"]:
            summary_strings.append("artifact_only: passed all timing-lock rules")
        else:
            summary_strings.append("not_artifact_only: " + " | ".join(failed))

    out["artifact_only_pass_reasons"] = pass_strings
    out["artifact_only_fail_reasons"] = fail_strings
    out["artifact_only_reason"] = summary_strings
    return out


def merge_artifact_metrics_with_bombcell(
    artifact_df: pd.DataFrame,
    quality_metrics_df: pd.DataFrame,
) -> pd.DataFrame:
    merged = artifact_df.merge(
        quality_metrics_df,
        on="cluster_id",
        how="left",
        suffixes=("", "_bc"),
    )
    return merged.sort_values(
        ["artifact_only_candidate", "artifact_score", "pulse_hit_rate", "fraction_spikes_locked"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)


def export_phy_artifact_tsvs(
    ks_dir: str | Path,
    results_df: pd.DataFrame,
    *,
    label_col: str = "artifact_only_candidate",
    reason_col: str = "artifact_only_reason",
) -> dict[str, Path]:
    ks_dir = Path(ks_dir)
    if "cluster_id" not in results_df.columns:
        raise KeyError("results_df must contain a 'cluster_id' column.")
    if label_col not in results_df.columns:
        raise KeyError(f"results_df must contain '{label_col}'.")
    if reason_col not in results_df.columns:
        raise KeyError(f"results_df must contain '{reason_col}'.")

    cluster_ids = pd.to_numeric(results_df["cluster_id"], errors="coerce")
    valid = cluster_ids.notna()

    label_df = pd.DataFrame(
        {
            "cluster_id": cluster_ids[valid].astype(int),
            "artifactOnly": np.where(
                results_df.loc[valid, label_col].astype(bool),
                "artifact_only",
                "not_artifact_only",
            ),
        }
    )
    reason_df = pd.DataFrame(
        {
            "cluster_id": cluster_ids[valid].astype(int),
            "artifactOnlyReason": results_df.loc[valid, reason_col].astype(str).to_numpy(),
        }
    )

    label_path = ks_dir / "cluster_artifactOnly.tsv"
    reason_path = ks_dir / "cluster_artifactOnlyReason.tsv"
    label_df.to_csv(label_path, sep="\t", index=False)
    reason_df.to_csv(reason_path, sep="\t", index=False)

    return {
        "label_tsv": label_path,
        "reason_tsv": reason_path,
    }
