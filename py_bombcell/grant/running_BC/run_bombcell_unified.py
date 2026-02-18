from __future__ import annotations

import argparse
import json
import shutil
import traceback
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

import bombcell as bc

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from grant_config import get_probe_mode_overrides, load_grant_config


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    return obj


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

        qm_path = probe_out / f"Probe_{probe}_quality_metrics.csv"
        counts_path = probe_out / f"Probe_{probe}_unit_type_counts.csv"
        param_path = probe_out / f"Probe_{probe}_param.json"

        if not overwrite and any(p.exists() for p in [qm_path, counts_path, param_path]):
            raise FileExistsError(f"Refusing to overwrite export files in {probe_out}")

        qm.to_csv(qm_path, index=False)
        counts = unit_types.value_counts().rename_axis("unit_type").reset_index(name="count")
        counts.to_csv(counts_path, index=False)
        with param_path.open("w", encoding="utf-8") as f:
            json.dump(entry["param"], f, indent=2, default=_json_safe)

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
        save_subdir = "DEFAULT"
    elif args.mode == "np20_rerun":
        staging_root = cfg["np20_ks_staging_root"]
        export_root = cfg["np20_export_root"]
        save_subdir = "NP2_RERUN"
    else:
        staging_root = cfg["bombcell_singleprobe_root"]
        export_root = cfg["single_export_root"]
        save_subdir = "SINGLE_PROBE"

    staged_dirs = stage_kilosort4(cfg["probe_kilosort_dirs"], staging_root, probes, overwrite=args.overwrite)

    results: Dict[str, Dict[str, Any]] = {}
    for probe in probes:
        ks_dir = staged_dirs[probe]
        raw_file = cfg["continuous_dat_paths"][probe]
        meta_file = cfg["structure_oebin"]
        save_path = ks_dir / "bombcell" / save_subdir
        save_path.mkdir(parents=True, exist_ok=True)

        print(f"\n=== Probe {probe} ({cfg['probe_regions'].get(probe, 'unknown region')}) ===")
        print(f"ks_dir: {ks_dir}")
        print(f"raw_file: {raw_file}")
        print(f"meta_file: {meta_file}")

        try:
            param = bc.get_default_parameters(str(ks_dir), raw_file=str(raw_file), meta_file=str(meta_file), kilosort_version=4)
            overrides = get_probe_mode_overrides(cfg, probe, args.mode)
            if overrides:
                print(f"Applying overrides for probe {probe}: {overrides}")
            param.update(overrides)

            quality_metrics, param_out, unit_type, unit_type_string = bc.run_bombcell(str(ks_dir), str(save_path), param)
            results[probe] = {
                "ks_dir": ks_dir,
                "save_path": save_path,
                "quality_metrics": quality_metrics,
                "param": param_out,
                "unit_type": unit_type,
                "unit_type_string": unit_type_string,
            }
            print(pd.Series(unit_type_string).value_counts())
        except Exception as exc:
            traceback.print_exc()
            results[probe] = {"ks_dir": ks_dir, "save_path": save_path, "error": repr(exc)}

    export_results(results, export_root, probes, overwrite=args.overwrite)
    print(f"\nExport complete: {export_root}")


if __name__ == "__main__":
    main()
