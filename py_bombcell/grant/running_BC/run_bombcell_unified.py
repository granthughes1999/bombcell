from __future__ import annotations

import argparse
import json
import shutil
import traceback
from pathlib import Path
from typing import Any, Dict, Iterable, List

import numpy as np
import pandas as pd

import bombcell as bc

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from grant_config import get_probe_mode_overrides, load_grant_config

BC_ROI_LABEL_COLUMN = "bc_roiLabel"


# def _json_safe(obj: Any) -> Any:
#     if isinstance(obj, Path):
#         return str(obj)
#     return obj

# new code
def _to_jsonable(obj: Any, _seen: set[int] | None = None) -> Any:
    if _seen is None:
        _seen = set()

    oid = id(obj)
    if isinstance(obj, (dict, list, tuple, set)):
        if oid in _seen:
            return "<CIRCULAR_REF>"
        _seen.add(oid)

    if isinstance(obj, Path):
        return str(obj)

    # numpy scalars/arrays
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()

    # pandas objects (if any leak into param_out)
    if isinstance(obj, (pd.Series, pd.Index)):
        return obj.tolist()
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="list")

    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v, _seen) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(v, _seen) for v in obj]

    # allow JSON-native types
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # fallback: stringify unknown objects
    return repr(obj)

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
    if tip_position == "min_y":
        dist_um = unit_y - float(np.nanmin(shank_y))
    elif tip_position == "max_y":
        dist_um = float(np.nanmax(shank_y)) - unit_y
    else:
        raise ValueError("tip_position must be 'min_y' or 'max_y'.")

    return np.where(dist_um <= float(roi_end_um), in_label, out_label)


def save_phy_roi_labels(ks_dir: Path, cluster_ids: np.ndarray, roi_labels: np.ndarray) -> None:
    out_tsv = ks_dir / "cluster_bc_roiLabel.tsv"
    pd.DataFrame({"cluster_id": cluster_ids.astype(int), BC_ROI_LABEL_COLUMN: roi_labels}).to_csv(
        out_tsv, sep="\t", index=False
    )


def stage_kilosort4(source_dirs: Dict[str, Path], dst_root: Path, probes: Iterable[str], overwrite: bool) -> Dict[str, Path]:
    dst_root.mkdir(parents=True, exist_ok=True)
    staged: Dict[str, Path] = {}
    for probe in probes:
        src = source_dirs[probe]
        dst = dst_root / f"kilosort4_{probe}"
        if not src.exists():
            raise FileNotFoundError(f"Missing kilosort4 folder for probe {probe}: {src}")
        if dst.exists():
            if overwrite:
                shutil.rmtree(dst)
            else:
                raise FileExistsError(f"Destination exists: {dst} (use --overwrite to replace)")
        shutil.copytree(src, dst)
        staged[probe] = dst
    return staged


def export_results(results: Dict[str, Dict[str, Any]], output_root: Path, probes: Iterable[str], overwrite: bool) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []

    for probe in probes:
        entry = results.get(probe, {})
        probe_out = output_root / f"Probe_{probe}"
        probe_out.mkdir(parents=True, exist_ok=True)

        if "quality_metrics" not in entry:
            (probe_out / "ERROR.txt").write_text(entry.get("error", "Unknown error"), encoding="utf-8")
            rows.append({"probe": probe, "status": "FAILED", "error": entry.get("error", "Unknown error")})
            continue

        qm = pd.DataFrame(entry["quality_metrics"]).reset_index().rename(columns={"index": "cluster_id"})
        unit_types = pd.Series(entry["unit_type_string"], name="Bombcell_unit_type")
        qm.insert(0, "Bombcell_unit_type", unit_types)
        if "roi_label" in entry and len(entry["roi_label"]) == len(qm):
            qm.insert(1, BC_ROI_LABEL_COLUMN, pd.Series(entry["roi_label"]))

        qm_path = probe_out / f"Probe_{probe}_quality_metrics.csv"
        counts_path = probe_out / f"Probe_{probe}_unit_type_counts.csv"
        param_path = probe_out / f"Probe_{probe}_param.json"

        if not overwrite and any(p.exists() for p in [qm_path, counts_path, param_path]):
            raise FileExistsError(f"Refusing to overwrite export files in {probe_out}")

        qm.to_csv(qm_path, index=False)
        counts = unit_types.value_counts().rename_axis("unit_type").reset_index(name="count")
        counts.to_csv(counts_path, index=False)
        # new code
        with param_path.open("w", encoding="utf-8") as f:
            json.dump(_to_jsonable(entry["param"]), f, indent=2)

        row = {"probe": probe, "status": "OK", "ks_dir": str(entry["ks_dir"]), "save_path": str(entry["save_path"])}
        for _, count_row in counts.iterrows():
            row[f"n_{count_row['unit_type']}"] = int(count_row["count"])
        rows.append(row)

    pd.DataFrame(rows).to_csv(output_root / "batch_summary.csv", index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified Bombcell runner for Grant workflows")
    parser.add_argument("--config", type=str, default=None, help="Path to grant_recording_config.json")
    parser.add_argument(
        "--mode",
        choices=["batch", "single_probe", "np20_rerun"],
        default="batch",
        help="Run mode",
    )
    parser.add_argument("--target-probe", type=str, default=None, help="Required for single_probe mode")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite staged/exported outputs")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_grant_config(args.config)

    if args.mode == "single_probe":
        if not args.target_probe:
            raise ValueError("--target-probe is required in single_probe mode")
        probes = [args.target_probe.upper()]
    elif args.mode == "np20_rerun":
        probes = cfg["np20_probes"]
    else:
        probes = cfg["probes_all"]

    if args.mode == "batch":
        staging_root = cfg["default_ks_staging_root"]
        export_root = cfg["default_export_root"]
    elif args.mode == "np20_rerun":
        staging_root = cfg["np20_ks_staging_root"]
        export_root = cfg["np20_export_root"]
    else:
        staging_root = cfg["bombcell_singleprobe_root"]
        export_root = cfg["single_export_root"]

    staged_dirs = stage_kilosort4(cfg["probe_kilosort_dirs"], staging_root, probes, overwrite=args.overwrite)

    results: Dict[str, Dict[str, Any]] = {}
    for probe in probes:
        ks_dir = staged_dirs[probe]
        raw_file = cfg["continuous_dat_paths"][probe]
        meta_file = cfg["structure_oebin"]
        save_path = ks_dir / "bombcell"
        save_path.mkdir(parents=True, exist_ok=True)

        print(f"\n=== Probe {probe} ({cfg['probe_regions'].get(probe, 'unknown region')}) ===")
        print(f"ks_dir: {ks_dir}")
        print(f"raw_file: {raw_file}")
        print(f"meta_file: {meta_file}")

        try:
            param = bc.get_default_parameters(str(ks_dir), raw_file=str(raw_file), meta_file=str(meta_file), kilosort_version=4)
            param['extractRaw'] = True
            overrides = get_probe_mode_overrides(cfg, probe, args.mode)
            if overrides:
                print(f"Applying overrides for probe {probe}: {overrides}")
            param.update(overrides)
            print("\n=== FINAL BombCell params (after overrides) ===")
            for k in sorted(overrides.keys()):
                print(f"{k}: {param.get(k)}")
            print("=== END FINAL PARAMS ===\n")
            quality_metrics, param_out, unit_type, unit_type_string = bc.run_bombcell(str(ks_dir), str(save_path), param)
            roi_label = None
            # dict mapping probe name to max IN_ROI distance from tip (um)
            # current ROI labeling uses compute_roi_labels default tip_position='min_y'
            roi_config = cfg.get("probe_recording_roi", {})
            roi_end = roi_config.get(probe)
            if roi_end is not None:
                roi_label = compute_roi_labels(quality_metrics, ks_dir, roi_end_um=float(roi_end))
                # unique_templates is the canonical per-row unit ID order produced by Bombcell.
                # phy_clusterID is used as a fallback when unique_templates is unavailable.
                if "unique_templates" in param_out:
                    cluster_ids = np.asarray(param_out["unique_templates"])
                elif "phy_clusterID" in quality_metrics:
                    cluster_ids = np.asarray(quality_metrics["phy_clusterID"])
                else:
                    raise KeyError(
                        f"Could not determine cluster IDs for ROI label export for probe {probe}. "
                        "Expected param_out['unique_templates'] or quality_metrics['phy_clusterID']."
                    )
                if len(cluster_ids) == len(roi_label):
                    save_phy_roi_labels(ks_dir, cluster_ids, roi_label)
                else:
                    raise ValueError(
                        f"cluster_bc_roiLabel.tsv export failed for probe {probe}: "
                        f"cluster_ids length ({len(cluster_ids)}) != roi_labels length ({len(roi_label)})."
                    )
            results[probe] = {
                "ks_dir": ks_dir,
                "save_path": save_path,
                "quality_metrics": quality_metrics,
                "param": param_out,
                "unit_type": unit_type,
                "unit_type_string": unit_type_string,
                "roi_label": roi_label,
            }
            print(pd.Series(unit_type_string).value_counts())
        except Exception as exc:
            traceback.print_exc()
            results[probe] = {"ks_dir": ks_dir, "save_path": save_path, "error": repr(exc)}

    export_results(results, export_root, probes, overwrite=args.overwrite)
    print(f"\nExport complete: {export_root}")


if __name__ == "__main__":
    main()
