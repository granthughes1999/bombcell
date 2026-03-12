from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from helper_func.grant_config import load_grant_config  # noqa: E402
from mice.Reach15.helper_func.nwb_data_prep_v2 import build_session_grant_config, load_env  # noqa: E402


SESSION_SUFFIX = {1: "", 2: "_01", 3: "_02"}
PHY_EXPORT_COLUMNS = ["cluster_id", "bc_classificationReason"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build one clean all-probes BombCell classification-reason table from the "
            "Reach15 .env/session config flow, and optionally export/update the Phy-facing TSV files."
        )
    )
    parser.add_argument("--env-path", type=str, default=None, help="Optional path to the .env file.")
    parser.add_argument(
        "--session-selection",
        type=int,
        choices=(1, 2, 3),
        default=1,
        help="Which session block to use from the .env file.",
    )
    parser.add_argument(
        "--probes",
        type=str,
        default=None,
        help="Optional comma-separated probe list. Default: all kilosort4_* folders found in the selected BombCell root.",
    )
    parser.add_argument(
        "--write-phy-tsv",
        action="store_true",
        help="Write cluster_bc_classificationReason.tsv into each kilosort4_* folder.",
    )
    parser.add_argument(
        "--update-cluster-info",
        action="store_true",
        help="If cluster_info.tsv exists, merge the new BombCell reason columns into it.",
    )
    parser.add_argument(
        "--output-name",
        type=str,
        default="bc_classification_reason_all_probes.csv",
        help="Filename for the combined all-probes table written at the selected BombCell root.",
    )
    return parser.parse_args()


def _session_key(session_selection: int, key: str) -> str:
    return f"{key}{SESSION_SUFFIX[session_selection]}"


def _parse_probes(raw_value: str | None) -> list[str] | None:
    if raw_value is None:
        return None
    probes = [item.strip().upper() for item in raw_value.split(",") if item.strip()]
    return probes or None


def _infer_probe_from_dir(ks_dir: Path) -> str:
    suffix = ks_dir.name.replace("kilosort4_", "").strip()
    if not suffix:
        raise ValueError(f"Could not infer probe name from directory: {ks_dir}")
    return suffix[0].upper()


def _load_json(json_path: Path) -> dict[str, Any]:
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _candidate_probe_files(ks_dir: Path, probe: str) -> tuple[list[Path], list[Path]]:
    probe_upper = probe.upper()
    probe_lower = probe.lower()
    qm_candidates = [
        ks_dir / "bombcell" / f"Probe_{probe_upper}_quality_metrics.csv",
        ks_dir / "bombcell" / f"probe_{probe_lower}_quality_metrics.csv",
    ]
    param_candidates = [
        ks_dir / "bombcell" / f"Probe_{probe_upper}_param.json",
        ks_dir / "bombcell" / f"probe_{probe_lower}_param.json",
    ]
    return qm_candidates, param_candidates


def _first_existing(paths: list[Path]) -> Path | None:
    return next((path for path in paths if path.exists()), None)


def _ensure_cluster_id(qm_df: pd.DataFrame) -> pd.DataFrame:
    out = qm_df.copy()
    for column in ("cluster_id", "phy_clusterID", "id"):
        if column in out.columns:
            out["cluster_id"] = pd.to_numeric(out[column], errors="coerce")
            return out
    out["cluster_id"] = np.arange(len(out), dtype=int)
    return out


def _load_optional_roi(ks_dir: Path) -> pd.Series | None:
    roi_path = ks_dir / "cluster_bc_roiLabel.tsv"
    if not roi_path.exists():
        return None
    roi_df = pd.read_csv(roi_path, sep="\t")
    if "cluster_id" not in roi_df.columns:
        return None
    roi_col = "bc_roiLabel" if "bc_roiLabel" in roi_df.columns else "bc_ROI" if "bc_ROI" in roi_df.columns else None
    if roi_col is None:
        return None
    roi_map = (
        roi_df[["cluster_id", roi_col]]
        .copy()
        .assign(cluster_id=lambda df: pd.to_numeric(df["cluster_id"], errors="coerce"))
        .dropna(subset=["cluster_id"])
        .drop_duplicates(subset=["cluster_id"], keep="last")
        .set_index("cluster_id")[roi_col]
    )
    return roi_map


def _col(qm_df: pd.DataFrame, name: str) -> pd.Series:
    if name in qm_df.columns:
        return qm_df[name]
    return pd.Series(np.nan, index=qm_df.index)


def _build_failure_maps(qm_df: pd.DataFrame, param: dict[str, Any]) -> tuple[dict[str, pd.Series], dict[str, pd.Series], dict[str, pd.Series]]:
    noise_fail: dict[str, pd.Series] = {
        "nPeaks>maxNPeaks": _col(qm_df, "nPeaks") > param["maxNPeaks"],
        "nTroughs>maxNTroughs": _col(qm_df, "nTroughs") > param["maxNTroughs"],
        "wvDuration<minWvDuration": _col(qm_df, "waveformDuration_peakTrough") < param["minWvDuration"],
        "wvDuration>maxWvDuration": _col(qm_df, "waveformDuration_peakTrough") > param["maxWvDuration"],
        "baselineFlatness>maxWvBaselineFraction": _col(qm_df, "waveformBaselineFlatness") > param["maxWvBaselineFraction"],
        "scndPeakToTroughRatio>maxScndPeakToTroughRatio_noise": _col(qm_df, "scndPeakToTroughRatio")
        > param["maxScndPeakToTroughRatio_noise"],
    }

    if bool(param.get("computeSpatialDecay", False)):
        if bool(param.get("spDecayLinFit", False)):
            noise_fail["spatialDecaySlope<minSpatialDecaySlope"] = _col(qm_df, "spatialDecaySlope") < param["minSpatialDecaySlope"]
        else:
            noise_fail["spatialDecaySlope<minSpatialDecaySlopeExp"] = _col(qm_df, "spatialDecaySlope") < param["minSpatialDecaySlopeExp"]
            noise_fail["spatialDecaySlope>maxSpatialDecaySlopeExp"] = _col(qm_df, "spatialDecaySlope") > param["maxSpatialDecaySlopeExp"]

    mua_fail: dict[str, pd.Series] = {
        "percentageSpikesMissing_gaussian>maxPercSpikesMissing": _col(qm_df, "percentageSpikesMissing_gaussian")
        > param["maxPercSpikesMissing"],
        "nSpikes<minNumSpikes": _col(qm_df, "nSpikes") < param["minNumSpikes"],
        "fractionRPVs_estimatedTauR>maxRPVviolations": _col(qm_df, "fractionRPVs_estimatedTauR") > param["maxRPVviolations"],
        "presenceRatio<minPresenceRatio": _col(qm_df, "presenceRatio") < param["minPresenceRatio"],
    }

    if bool(param.get("extractRaw", False)):
        mua_fail["rawAmplitude<minAmplitude"] = _col(qm_df, "rawAmplitude") < param["minAmplitude"]
        mua_fail["signalToNoiseRatio<minSNR"] = _col(qm_df, "signalToNoiseRatio") < param["minSNR"]

    if bool(param.get("computeDrift", False)):
        mua_fail["maxDriftEstimate>maxDrift"] = _col(qm_df, "maxDriftEstimate") > param["maxDrift"]

    if bool(param.get("computeDistanceMetrics", False)):
        mua_fail["isolationDistance<isoDmin"] = _col(qm_df, "isolationDistance") < param["isoDmin"]
        mua_fail["Lratio>lratioMax"] = _col(qm_df, "Lratio") > param["lratioMax"]

    nonsoma_fail: dict[str, pd.Series] = {
        "troughToPeak2Ratio<minTroughToPeak2Ratio_nonSomatic": _col(qm_df, "troughToPeak2Ratio")
        < param["minTroughToPeak2Ratio_nonSomatic"],
        "mainPeak_before_width<minWidthFirstPeak_nonSomatic": _col(qm_df, "mainPeak_before_width")
        < param["minWidthFirstPeak_nonSomatic"],
        "mainTrough_width<minWidthMainTrough_nonSomatic": _col(qm_df, "mainTrough_width")
        < param["minWidthMainTrough_nonSomatic"],
        "peak1ToPeak2Ratio>maxPeak1ToPeak2Ratio_nonSomatic": _col(qm_df, "peak1ToPeak2Ratio")
        > param["maxPeak1ToPeak2Ratio_nonSomatic"],
        "mainPeakToTroughRatio>maxMainPeakToTroughRatio_nonSomatic": _col(qm_df, "mainPeakToTroughRatio")
        > param["maxMainPeakToTroughRatio_nonSomatic"],
    }

    return noise_fail, mua_fail, nonsoma_fail


def _hits_for_row(idx: int, failure_map: dict[str, np.ndarray]) -> list[str]:
    return [name for name, values in failure_map.items() if bool(values[idx])]


def annotate_classification_reasons(qm_df: pd.DataFrame, param: dict[str, Any]) -> pd.DataFrame:
    out = _ensure_cluster_id(qm_df)

    label_column = None
    for candidate in ("bombcell_label", "Bombcell_unit_type", "bc_unitType"):
        if candidate in out.columns:
            label_column = candidate
            break
    if label_column is None:
        raise KeyError(
            "Could not find a BombCell unit label column. Expected one of "
            "['bombcell_label', 'Bombcell_unit_type', 'bc_unitType']."
        )

    noise_fail, mua_fail, nonsoma_fail = _build_failure_maps(out, param)
    noise_np = {name: np.asarray(values, dtype=bool) for name, values in noise_fail.items()}
    mua_np = {name: np.asarray(values, dtype=bool) for name, values in mua_fail.items()}
    nonsoma_np = {name: np.asarray(values, dtype=bool) for name, values in nonsoma_fail.items()}
    labels_np = out[label_column].astype(str).to_numpy()

    main_reasons: list[str] = []
    all_reasons: list[str] = []
    for idx, label in enumerate(labels_np):
        noise_hits = _hits_for_row(idx, noise_np)
        mua_hits = _hits_for_row(idx, mua_np)
        nonsoma_hits = _hits_for_row(idx, nonsoma_np)

        if label == "NOISE":
            main_reason = f"NOISE: {noise_hits[0]}" if noise_hits else "NOISE"
            reasons = [f"NOISE: {hit}" for hit in noise_hits] or ["NOISE"]
        elif label in ("MUA", "NON-SOMA MUA"):
            main_reason = f"MUA: {mua_hits[0]}" if mua_hits else "MUA"
            reasons = [f"MUA: {hit}" for hit in mua_hits] or ["MUA"]
        elif label in ("NON-SOMA", "NON-SOMA GOOD"):
            main_reason = f"NON-SOMA: {nonsoma_hits[0]}" if nonsoma_hits else "NON-SOMA"
            reasons = [f"NON-SOMA: {hit}" for hit in nonsoma_hits] or ["NON-SOMA"]
        elif label == "GOOD":
            main_reason = "GOOD: passed all thresholds"
            reasons = [main_reason]
        else:
            main_reason = label
            reasons = [label]

        main_reasons.append(main_reason)
        all_reasons.append(" | ".join(reasons))

    out["bc_unitType"] = out[label_column].astype(str)
    out["bc_classificationReason"] = main_reasons
    out["bc_classificationReasonsAll"] = all_reasons
    return out


def build_phy_export_df(annotated_df: pd.DataFrame, _ks_dir: Path) -> pd.DataFrame:
    export_df = annotated_df[["cluster_id", "bc_classificationReason"]].copy()
    export_df["cluster_id"] = pd.to_numeric(export_df["cluster_id"], errors="coerce")
    export_df = export_df.dropna(subset=["cluster_id"]).copy()
    export_df["cluster_id"] = export_df["cluster_id"].astype(int)

    if export_df["cluster_id"].duplicated().any():
        dupes = export_df.loc[export_df["cluster_id"].duplicated(keep=False), "cluster_id"].tolist()
        raise ValueError(f"Duplicate cluster_id values found for {ks_dir}: {dupes[:10]}")

    preferred_columns = [column for column in PHY_EXPORT_COLUMNS if column in export_df.columns]
    return export_df[preferred_columns]


def write_phy_reason_tsv(ks_dir: Path, export_df: pd.DataFrame) -> Path:
    out_path = ks_dir / "cluster_bc_classificationReason.tsv"
    export_df.to_csv(out_path, sep="\t", index=False)
    return out_path


def update_cluster_info_tsv(ks_dir: Path, export_df: pd.DataFrame) -> Path | None:
    cluster_info_path = ks_dir / "cluster_info.tsv"
    if not cluster_info_path.exists():
        return None

    cluster_info_df = pd.read_csv(cluster_info_path, sep="\t")
    join_key = "id" if "id" in cluster_info_df.columns else "cluster_id" if "cluster_id" in cluster_info_df.columns else None
    if join_key is None:
        raise KeyError(f"cluster_info.tsv at {cluster_info_path} has no 'id' or 'cluster_id' column.")

    new_columns = [column for column in export_df.columns if column != "cluster_id"]
    base_df = cluster_info_df.drop(columns=[column for column in new_columns if column in cluster_info_df.columns])

    if join_key == "id":
        merge_df = export_df.rename(columns={"cluster_id": "id"})
    else:
        merge_df = export_df.copy()

    merged = base_df.merge(merge_df, on=join_key, how="left")

    priority = ["id", "cluster_id", "ch", "bc_classificationReason", "KSLabel"]
    ordered = [column for column in priority if column in merged.columns]
    ordered.extend(column for column in merged.columns if column not in ordered)
    merged = merged[ordered]
    merged.to_csv(cluster_info_path, sep="\t", index=False)
    return cluster_info_path


def resolve_session_paths(env_path: str | None, session_selection: int) -> tuple[dict[str, str], dict[str, Any], Path]:
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
    return session_data, cfg, bombcell_root


def collect_probe_dirs(bombcell_root: Path, requested_probes: list[str] | None) -> dict[str, Path]:
    if not bombcell_root.exists():
        raise FileNotFoundError(f"BombCell root does not exist: {bombcell_root}")

    all_probe_dirs: dict[str, Path] = {}
    for ks_dir in sorted(p for p in bombcell_root.iterdir() if p.is_dir() and p.name.lower().startswith("kilosort4_")):
        all_probe_dirs[_infer_probe_from_dir(ks_dir)] = ks_dir

    if requested_probes is None:
        if not all_probe_dirs:
            raise FileNotFoundError(f"No kilosort4_* folders found under {bombcell_root}")
        return all_probe_dirs

    selected: dict[str, Path] = {}
    missing: list[str] = []
    for probe in requested_probes:
        if probe in all_probe_dirs:
            selected[probe] = all_probe_dirs[probe]
        else:
            missing.append(probe)
    if missing:
        raise FileNotFoundError(
            f"Requested probes not found under {bombcell_root}: {', '.join(missing)}"
        )
    return selected


def load_probe_results(ks_dir: Path, probe: str) -> tuple[pd.DataFrame, dict[str, Any], Path, Path]:
    qm_candidates, param_candidates = _candidate_probe_files(ks_dir, probe)
    qm_path = _first_existing(qm_candidates)
    param_path = _first_existing(param_candidates)
    if qm_path is None:
        raise FileNotFoundError(
            f"Missing quality metrics CSV for probe {probe} in {ks_dir}. Tried: {', '.join(str(p) for p in qm_candidates)}"
        )
    if param_path is None:
        raise FileNotFoundError(
            f"Missing param JSON for probe {probe} in {ks_dir}. Tried: {', '.join(str(p) for p in param_candidates)}"
        )

    qm_df = pd.read_csv(qm_path)
    param = _load_json(param_path)
    return qm_df, param, qm_path, param_path


def export_all_probes(
    bombcell_root: Path,
    requested_probes: list[str] | None = None,
    *,
    write_phy_tsv: bool = False,
    update_cluster_info: bool = False,
    output_name: str = "bc_classification_reason_all_probes.csv",
) -> Path:
    probe_dirs = collect_probe_dirs(bombcell_root, requested_probes)
    all_rows: list[pd.DataFrame] = []

    print(f"BombCell root: {bombcell_root}")
    print(f"Probes: {', '.join(probe_dirs.keys())}")

    for probe, ks_dir in probe_dirs.items():
        qm_df, param, qm_path, param_path = load_probe_results(ks_dir, probe)
        annotated_df = annotate_classification_reasons(qm_df, param)
        export_df = build_phy_export_df(annotated_df, ks_dir)

        if write_phy_tsv:
            out_tsv = write_phy_reason_tsv(ks_dir, export_df)
            print(f"[{probe}] wrote {out_tsv.name}")

        if update_cluster_info:
            updated = update_cluster_info_tsv(ks_dir, export_df)
            if updated is None:
                print(f"[{probe}] cluster_info.tsv not found, skipped")
            else:
                print(f"[{probe}] updated {updated.name}")

        combined_df = annotated_df.copy()
        combined_df.insert(0, "probe", probe)
        combined_df["ks_dir"] = str(ks_dir)
        combined_df["quality_metrics_path"] = str(qm_path)
        combined_df["param_path"] = str(param_path)

        if "bc_ROI" not in combined_df.columns:
            roi_map = _load_optional_roi(ks_dir)
            if roi_map is not None:
                combined_df["bc_ROI"] = combined_df["cluster_id"].map(roi_map)

        preferred = [
            "probe",
            "cluster_id",
            "bc_unitType",
            "bc_classificationReason",
            "bc_classificationReasonsAll",
            "bc_ROI",
            "ks_dir",
            "quality_metrics_path",
            "param_path",
        ]
        ordered = [column for column in preferred if column in combined_df.columns]
        ordered.extend(column for column in combined_df.columns if column not in ordered)
        all_rows.append(combined_df[ordered])

    output_path = bombcell_root / output_name
    pd.concat(all_rows, ignore_index=True).to_csv(output_path, index=False)
    print(f"Wrote combined table: {output_path}")
    return output_path


def main() -> None:
    args = parse_args()
    requested_probes = _parse_probes(args.probes)
    _, cfg, bombcell_root = resolve_session_paths(args.env_path, args.session_selection)

    print(f"Recording root: {cfg['recording_root']}")
    print(f"Selected BombCell root: {bombcell_root}")
    if args.update_cluster_info:
        print("cluster_info.tsv updates assume Phy is closed.")

    export_all_probes(
        bombcell_root=bombcell_root,
        requested_probes=requested_probes,
        write_phy_tsv=args.write_phy_tsv,
        update_cluster_info=args.update_cluster_info,
        output_name=args.output_name,
    )


if __name__ == "__main__":
    main()
