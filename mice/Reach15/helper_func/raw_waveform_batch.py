from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from helper_func.grant_config import load_grant_config
from helper_func.nwb_data_prep import build_session_grant_config, load_env


SESSION_SUFFIX = {1: "", 2: "_01", 3: "_02"}


def _session_key(session_selection: int, key: str) -> str:
    return f"{key}{SESSION_SUFFIX[session_selection]}"


def _parse_probes(raw_value: str | list[str] | None) -> list[str] | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, str):
        probes = [item.strip().upper() for item in raw_value.split(",") if item.strip()]
    else:
        probes = [str(item).strip().upper() for item in raw_value if str(item).strip()]
    return probes or None


def resolve_session_waveform_context(
    env_path: str | Path | None = None,
    session_selection: int = 1,
) -> tuple[dict[str, str], dict[str, Any], Path, dict[str, Path]]:
    session_data = load_env(env_path)
    config_path, _ = build_session_grant_config(
        session_data_dic=session_data,
        session_selection=session_selection,
        verbose=False,
    )
    cfg = load_grant_config(config_path)

    np_file = session_data[_session_key(session_selection, "NP_FILE")]
    bombcell_folder = session_data[_session_key(session_selection, "BOMBCELL")]
    bombcell_root = Path(cfg["recordings_root"]) / np_file / "bombcell" / bombcell_folder
    raw_path_by_probe = {probe: Path(path) for probe, path in cfg["continuous_dat_paths"].items()}
    return session_data, cfg, bombcell_root, raw_path_by_probe


def collect_probe_contexts(
    bombcell_root: Path,
    raw_path_by_probe: dict[str, Path],
    probes: list[str] | None = None,
) -> dict[str, dict[str, Path]]:
    requested_probes = _parse_probes(probes)
    ks_dirs = {
        path.name.replace("kilosort4_", "").strip().upper(): path
        for path in sorted(bombcell_root.iterdir())
        if path.is_dir() and path.name.lower().startswith("kilosort4_")
    }
    if not ks_dirs:
        raise FileNotFoundError(f"No kilosort4_* folders found under {bombcell_root}")

    if requested_probes is None:
        selected = sorted(ks_dirs.keys())
    else:
        missing = [probe for probe in requested_probes if probe not in ks_dirs]
        if missing:
            raise FileNotFoundError(f"Missing probes under {bombcell_root}: {', '.join(missing)}")
        selected = requested_probes

    contexts: dict[str, dict[str, Path]] = {}
    for probe in selected:
        raw_path = raw_path_by_probe.get(probe)
        if raw_path is None:
            raise KeyError(f"No raw binary path found in config for probe {probe}")
        contexts[probe] = {"ks_dir": ks_dirs[probe], "bin_path": raw_path}
    return contexts


def _first_existing(paths: list[Path]) -> Path | None:
    return next((path for path in paths if path.exists()), None)


def load_probe_quality_metrics(ks_dir: Path, probe: str) -> pd.DataFrame | None:
    probe_upper = probe.upper()
    probe_lower = probe.lower()
    qm_candidates = [
        ks_dir / "bombcell" / f"Probe_{probe_upper}_quality_metrics.csv",
        ks_dir / "bombcell" / f"probe_{probe_lower}_quality_metrics.csv",
    ]
    qm_path = _first_existing(qm_candidates)
    if qm_path is None:
        return None
    qm_df = pd.read_csv(qm_path)
    for column in ("cluster_id", "phy_clusterID", "id"):
        if column in qm_df.columns:
            qm_df["cluster_id"] = pd.to_numeric(qm_df[column], errors="coerce")
            break
    if "cluster_id" not in qm_df.columns:
        qm_df["cluster_id"] = np.arange(len(qm_df), dtype=int)
    return qm_df


def choose_clusters_for_probe(
    qm_df: pd.DataFrame | None,
    *,
    max_units: int | None = None,
    label_filter: str | list[str] | None = None,
    explicit_cluster_ids: list[int] | None = None,
) -> list[int]:
    if explicit_cluster_ids is not None:
        return [int(cluster_id) for cluster_id in explicit_cluster_ids]
    if qm_df is None or qm_df.empty:
        return []

    out = qm_df.copy()
    out = out.dropna(subset=["cluster_id"]).copy()
    out["cluster_id"] = out["cluster_id"].astype(int)

    if label_filter is not None:
        if isinstance(label_filter, str):
            labels = {label_filter}
        else:
            labels = {str(item) for item in label_filter}
        label_col = "Bombcell_unit_type" if "Bombcell_unit_type" in out.columns else "bombcell_label" if "bombcell_label" in out.columns else None
        if label_col is not None:
            out = out[out[label_col].astype(str).isin(labels)].copy()

    if out.empty:
        return []

    sort_columns = [column for column in ["rawAmplitude", "signalToNoiseRatio", "nSpikes", "cluster_id"] if column in out.columns]
    ascending = [False if column != "cluster_id" else True for column in sort_columns]
    out = out.sort_values(sort_columns, ascending=ascending).drop_duplicates(subset=["cluster_id"])
    cluster_ids = out["cluster_id"].astype(int).tolist()
    if max_units is None:
        return cluster_ids
    return cluster_ids[: int(max_units)]


def load_ks4_sorting(folder: str | Path) -> tuple[np.ndarray, np.ndarray]:
    folder = str(folder)
    spike_times = np.load(os.path.join(folder, "spike_times.npy")).astype(np.int64).squeeze()
    spike_clusters = np.load(os.path.join(folder, "spike_clusters.npy")).astype(np.int64).squeeze()
    return spike_times, spike_clusters


def open_memmap_binary(bin_path: str | Path, n_channels: int, dtype: Any = np.int16) -> tuple[np.memmap, int]:
    mm = np.memmap(bin_path, dtype=dtype, mode="r")
    n_samp = mm.size // int(n_channels)
    if n_samp * int(n_channels) != mm.size:
        raise ValueError(f"Binary size {mm.size} not divisible by n_channels={n_channels}")
    return mm.reshape(n_samp, int(n_channels)), n_samp


def estimate_peak_channel(
    ks_folder: str | Path,
    bin_path: str | Path,
    cluster_id: int,
    n_channels: int,
    *,
    fs: int = 30000,
    n_spikes_scan: int = 200,
    pre_ms: float = 1.0,
    post_ms: float = 2.0,
    dtype: Any = np.int16,
    seed: int = 0,
    ignore_edges_s: float = 1.0,
) -> int:
    spike_times, spike_clusters = load_ks4_sorting(ks_folder)
    spike_samples = spike_times[spike_clusters == int(cluster_id)]
    spike_samples.sort()
    if spike_samples.size == 0:
        raise ValueError(f"No spikes found for cluster {cluster_id}")

    mm, n_samp = open_memmap_binary(bin_path, n_channels, dtype=dtype)
    pre_samp = int(round(pre_ms * 1e-3 * fs))
    post_samp = int(round(post_ms * 1e-3 * fs))
    center_idx = pre_samp

    edge = int(ignore_edges_s * fs)
    valid = spike_samples[(spike_samples > edge + pre_samp) & (spike_samples < (n_samp - edge - post_samp - 1))]
    if valid.size == 0:
        raise ValueError("No spikes remain after edge exclusion; adjust ignore_edges_s or window.")

    rng = np.random.default_rng(seed)
    pick = valid if valid.size <= n_spikes_scan else rng.choice(valid, size=n_spikes_scan, replace=False)
    acc = np.zeros(int(n_channels), dtype=np.float64)
    for sample in pick:
        start = int(sample) - pre_samp
        stop = int(sample) + post_samp
        snip = mm[start:stop, :]
        acc += np.abs(snip[center_idx, :])
    return int(np.argmax(acc))


def ks_best_channel_for_cluster(ks_folder: str | Path, cluster_id: int) -> tuple[int, int]:
    ks_folder = str(ks_folder)
    spike_clusters = np.load(os.path.join(ks_folder, "spike_clusters.npy")).astype(np.int64).squeeze()
    spike_templates = np.load(os.path.join(ks_folder, "spike_templates.npy")).astype(np.int64).squeeze()
    templates = np.load(os.path.join(ks_folder, "templates.npy"))

    idx = np.where(spike_clusters == int(cluster_id))[0]
    if idx.size == 0:
        raise ValueError(f"No spikes found for cluster {cluster_id}")

    dominant_template = int(np.bincount(spike_templates[idx]).argmax())
    template = templates[dominant_template]
    ptp_per_ch = template.max(axis=0) - template.min(axis=0)
    best_ch_in_templates = int(np.argmax(ptp_per_ch))

    chmap_path = os.path.join(ks_folder, "channel_map.npy")
    if os.path.exists(chmap_path):
        channel_map = np.load(chmap_path).astype(np.int64).squeeze()
        best_channel = int(channel_map[best_ch_in_templates])
    else:
        best_channel = best_ch_in_templates
    return best_channel, dominant_template


def _center_channel_from_qm(qm_df: pd.DataFrame | None, cluster_id: int) -> int | None:
    if qm_df is None or "maxChannels" not in qm_df.columns or "cluster_id" not in qm_df.columns:
        return None
    cluster_ids = pd.to_numeric(qm_df["cluster_id"], errors="coerce")
    sub = qm_df.loc[cluster_ids == int(cluster_id)]
    if sub.empty:
        return None
    value = pd.to_numeric(sub.iloc[0]["maxChannels"], errors="coerce")
    if pd.isna(value):
        return None
    return int(value)


def plot_raw_traces_for_cluster(
    ks_folder: str | Path,
    bin_path: str | Path,
    cluster_id: int,
    n_channels: int,
    *,
    fs: int = 30000,
    center_chan: int,
    neighbor_radius: int = 6,
    n_spikes_to_plot: int = 40,
    pre_ms: float = 2.0,
    post_ms: float = 3.0,
    dtype: Any = np.int16,
    seed: int = 0,
    ignore_edges_s: float = 1.0,
    show: bool = False,
) -> tuple[dict[str, Any], plt.Figure, plt.Figure]:
    spike_times, spike_clusters = load_ks4_sorting(ks_folder)
    spike_samples = spike_times[spike_clusters == int(cluster_id)]
    spike_samples.sort()
    if spike_samples.size == 0:
        raise ValueError(f"No spikes found for cluster {cluster_id}")

    mm, n_samp = open_memmap_binary(bin_path, n_channels, dtype=dtype)
    pre_samp = int(round(pre_ms * 1e-3 * fs))
    post_samp = int(round(post_ms * 1e-3 * fs))
    win = pre_samp + post_samp

    center_chan = int(center_chan)
    chans = np.arange(max(0, center_chan - neighbor_radius), min(int(n_channels), center_chan + neighbor_radius + 1))

    edge = int(ignore_edges_s * fs)
    valid = spike_samples[(spike_samples > edge + pre_samp) & (spike_samples < (n_samp - edge - post_samp - 1))]
    if valid.size == 0:
        raise ValueError("No spikes remain after edge exclusion; adjust ignore_edges_s or window.")

    rng = np.random.default_rng(seed)
    pick = valid if valid.size <= n_spikes_to_plot else rng.choice(valid, size=n_spikes_to_plot, replace=False)
    pick.sort()

    snippets = []
    for sample in pick:
        start = int(sample) - pre_samp
        stop = int(sample) + post_samp
        snippets.append(mm[start:stop, :][:, chans])

    X = np.stack(snippets, axis=0)
    t_ms = (np.arange(win) - pre_samp) * 1e3 / fs

    fig_overlay, axes = plt.subplots(len(chans), 1, figsize=(10, 1.5 * len(chans)), sharex=True)
    if len(chans) == 1:
        axes = [axes]
    for idx, ch in enumerate(chans):
        axes[idx].plot(t_ms, X[:, :, idx].T, linewidth=0.45, alpha=0.22)
        axes[idx].axvline(0, linewidth=1)
        axes[idx].set_ylabel(f"ch {int(ch)}")
    axes[-1].set_xlabel("time (ms)")
    fig_overlay.suptitle(f"Probe raw snippets | cluster {cluster_id} | center_chan={center_chan}")
    fig_overlay.tight_layout()

    mean_waveform = X.mean(axis=0)
    fig_mean, axes = plt.subplots(len(chans), 1, figsize=(10, 1.3 * len(chans)), sharex=True)
    if len(chans) == 1:
        axes = [axes]
    for idx, ch in enumerate(chans):
        axes[idx].plot(t_ms, mean_waveform[:, idx], linewidth=1.4)
        axes[idx].axvline(0, linewidth=1)
        axes[idx].set_ylabel(f"ch {int(ch)}")
    axes[-1].set_xlabel("time (ms)")
    fig_mean.suptitle(f"Probe mean raw waveform | cluster {cluster_id}")
    fig_mean.tight_layout()

    if show:
        plt.show()
    else:
        plt.close(fig_overlay)
        plt.close(fig_mean)

    meta = {
        "cluster_id": int(cluster_id),
        "n_spikes_total": int(spike_samples.size),
        "n_spikes_plotted": int(X.shape[0]),
        "center_chan": int(center_chan),
        "neighbor_radius": int(neighbor_radius),
        "channels_shown": chans.astype(int).tolist(),
        "fs": int(fs),
        "pre_ms": float(pre_ms),
        "post_ms": float(post_ms),
    }
    return meta, fig_overlay, fig_mean


def save_cluster_waveform_plots(
    ks_dir: Path,
    bin_path: Path,
    cluster_id: int,
    mean_output_dir: Path,
    overlay_output_dir: Path,
    *,
    probe: str,
    n_channels: int = 384,
    fs: int = 30000,
    neighbor_radius: int = 6,
    n_spikes_to_plot: int = 40,
    pre_ms: float = 2.0,
    post_ms: float = 3.0,
    dtype: Any = np.int16,
    seed: int = 0,
    ignore_edges_s: float = 1.0,
    center_chan: int | None = None,
    qm_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    mean_output_dir.mkdir(parents=True, exist_ok=True)
    overlay_output_dir.mkdir(parents=True, exist_ok=True)

    resolved_center = center_chan
    center_source = "explicit"
    if resolved_center is None:
        resolved_center = _center_channel_from_qm(qm_df, cluster_id)
        center_source = "quality_metrics.maxChannels"
    if resolved_center is None:
        try:
            resolved_center, _ = ks_best_channel_for_cluster(ks_dir, cluster_id)
            center_source = "kilosort_template"
        except Exception:
            resolved_center = estimate_peak_channel(
                ks_folder=ks_dir,
                bin_path=bin_path,
                cluster_id=cluster_id,
                n_channels=n_channels,
                fs=fs,
                dtype=dtype,
                seed=seed,
                ignore_edges_s=ignore_edges_s,
            )
            center_source = "raw_peak_estimate"

    meta, fig_overlay, fig_mean = plot_raw_traces_for_cluster(
        ks_folder=ks_dir,
        bin_path=bin_path,
        cluster_id=cluster_id,
        n_channels=n_channels,
        fs=fs,
        center_chan=resolved_center,
        neighbor_radius=neighbor_radius,
        n_spikes_to_plot=n_spikes_to_plot,
        pre_ms=pre_ms,
        post_ms=post_ms,
        dtype=dtype,
        seed=seed,
        ignore_edges_s=ignore_edges_s,
        show=False,
    )

    mean_path = mean_output_dir / f"probe_{probe}_cluster_{int(cluster_id):04d}_raw_mean.png"
    overlay_path = overlay_output_dir / f"probe_{probe}_cluster_{int(cluster_id):04d}_raw_overlay.png"
    fig_mean.savefig(mean_path, dpi=220, bbox_inches="tight")
    fig_overlay.savefig(overlay_path, dpi=220, bbox_inches="tight")
    plt.close(fig_overlay)
    plt.close(fig_mean)

    meta.update(
        {
            "probe": probe,
            "ks_dir": str(ks_dir),
            "bin_path": str(bin_path),
            "center_channel_source": center_source,
            "overlay_path": str(overlay_path),
            "mean_path": str(mean_path),
        }
    )
    return meta


def render_raw_waveform_batch(
    bombcell_root: Path,
    raw_path_by_probe: dict[str, Path],
    *,
    probes: list[str] | None = None,
    clusters_by_probe: dict[str, list[int]] | None = None,
    max_units_per_probe: int | None = None,
    label_filter: str | list[str] | None = None,
    output_subdir: str | None = None,
    n_channels: int = 384,
    fs: int = 30000,
    neighbor_radius: int = 6,
    n_spikes_to_plot: int = 40,
    pre_ms: float = 2.0,
    post_ms: float = 3.0,
    dtype: Any = np.int16,
    seed: int = 0,
    ignore_edges_s: float = 1.0,
) -> tuple[pd.DataFrame, Path]:
    probe_contexts = collect_probe_contexts(bombcell_root, raw_path_by_probe, probes=probes)
    output_root = bombcell_root if output_subdir in (None, "", ".") else bombcell_root / output_subdir
    output_root.mkdir(parents=True, exist_ok=True)
    mean_root = output_root / "raw_mean"
    overlay_root = output_root / "raw_overlay"
    mean_root.mkdir(parents=True, exist_ok=True)
    overlay_root.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for probe, context in probe_contexts.items():
        ks_dir = context["ks_dir"]
        bin_path = context["bin_path"]
        qm_df = load_probe_quality_metrics(ks_dir, probe)
        explicit_cluster_ids = None if clusters_by_probe is None else clusters_by_probe.get(probe)
        cluster_ids = choose_clusters_for_probe(
            qm_df,
            max_units=max_units_per_probe,
            label_filter=label_filter,
            explicit_cluster_ids=explicit_cluster_ids,
        )
        if not cluster_ids:
            rows.append(
                {
                    "probe": probe,
                    "cluster_id": np.nan,
                    "status": "SKIPPED",
                    "error": "No clusters selected for plotting.",
                }
            )
            continue

        probe_mean_dir = mean_root / f"Probe_{probe}"
        probe_overlay_dir = overlay_root / f"Probe_{probe}"
        for cluster_id in cluster_ids:
            try:
                meta = save_cluster_waveform_plots(
                    ks_dir=ks_dir,
                    bin_path=bin_path,
                    cluster_id=int(cluster_id),
                    mean_output_dir=probe_mean_dir,
                    overlay_output_dir=probe_overlay_dir,
                    probe=probe,
                    n_channels=n_channels,
                    fs=fs,
                    neighbor_radius=neighbor_radius,
                    n_spikes_to_plot=n_spikes_to_plot,
                    pre_ms=pre_ms,
                    post_ms=post_ms,
                    dtype=dtype,
                    seed=seed,
                    ignore_edges_s=ignore_edges_s,
                    qm_df=qm_df,
                )
                meta["status"] = "OK"
                if qm_df is not None and "cluster_id" in qm_df.columns:
                    cluster_ids_num = pd.to_numeric(qm_df["cluster_id"], errors="coerce")
                    sub = qm_df.loc[cluster_ids_num == int(cluster_id)]
                    if not sub.empty:
                        for column in ["Bombcell_unit_type", "bombcell_label", "rawAmplitude", "signalToNoiseRatio", "nSpikes", "maxChannels"]:
                            if column in sub.columns:
                                meta[column] = sub.iloc[0][column]
                rows.append(meta)
            except Exception as exc:
                rows.append(
                    {
                        "probe": probe,
                        "cluster_id": int(cluster_id),
                        "status": "FAILED",
                        "error": repr(exc),
                        "ks_dir": str(ks_dir),
                        "bin_path": str(bin_path),
                    }
                )

    summary_df = pd.DataFrame(rows)
    summary_path = output_root / "raw_waveform_plot_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    return summary_df, output_root
