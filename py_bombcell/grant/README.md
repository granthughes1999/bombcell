# Grant Bombcell Workflows

## 1) Unified run entrypoint
Use one runner for all three workflows:

```bash
cd C:\Users\user\Documents\github\bombcell\py_bombcell
python grant/running_BC/run_bombcell_unified.py --config grant/configs/grant_recording_config.json --mode batch
python grant/running_BC/run_bombcell_unified.py --config grant/configs/grant_recording_config.json --mode single_probe --target-probe B
python grant/running_BC/run_bombcell_unified.py --config grant/configs/grant_recording_config.json --mode np20_rerun
```

For notebook-based per-probe parameter edits and post-run reloads, use:

- `grant/running_BC/BC_probe_param_and_reload.ipynb`
- `grant/running_BC/BC_add_roi_labels_to_phy.ipynb` (retroactively writes `cluster_bc_roiLabel.tsv` with `IN_ROI` / `OUT_ROI` for Phy without rerunning Bombcell)

This notebook shows how to:
- edit `probe_param_overrides` / `mode_param_overrides` directly in notebook cells,
- resolve `ks_dir` and `save_path` for a specific mode/probe,
- rerun `bc.plot_summary_data(...)`, `bc.compare_manual_vs_bombcell(save_path)`, and `bc.unit_quality_gui(...)`.
- label units by tip-distance ROI as `IN_ROI` / `OUTSIDE_ROI` (example: tip→950um on Probe B).

Bombcell save path convention (current):
- all run modes save directly to `.../kilosort4_<probe>/bombcell/`
- no nested run subfolders (`DEFAULT`, `NP2_RERUN`, `SINGLE_PROBE`)

ROI labeling helper is available in:
- `grant/analyzing_BC_results/post_analysis_setup.py` → `label_units_by_tip_distance(...)`

For class-by-class explanation of why each unit is GOOD/MUA/NOISE/NON-SOMATIC, use:
- `grant/analyzing_BC_results/BC_classification_reason_audit.ipynb`

To inspect recording-level Open Ephys metadata (`structure.oebin`) and verify probe streams, use:
- `grant/analyzing_BC_results/BC_inspect_structure_oebin.ipynb`
- `grant/analyzing_BC_results/BC_inspect_structure_obien.ipynb` (compatibility filename; same notebook content)

For simultaneous all-probe analysis with ROI-aware tables/plots, use:
- `grant/analyzing_BC_results/BC_all_probes_roi_dashboard.ipynb`

### IN_ROI / OUTSIDE_ROI usage
`IN_ROI` / `OUTSIDE_ROI` labels come from distance-to-tip thresholds:
1. Store per-probe ROI lengths (um from tip) in config JSON under `probe_recording_roi`.
2. Notebooks load these defaults automatically, and you can still override in-notebook (`ROI_OVERRIDE_BY_PROBE` / `ROI_END_UM_OVERRIDE`).
3. For each probe, units with `distance_from_tip_um <= ROI_END_UM_BY_PROBE[probe]` are `IN_ROI`.
3. Units above threshold are `OUTSIDE_ROI`.
4. If ROI is unset (`None`), the notebook marks units as `ROI_NOT_SET`.

When running via the unified Grant runner and `probe_recording_roi` is set, Phy gets:
- `cluster_bc_roiLabel.tsv` in each probe Kilosort folder
- column name: `bc_roiLabel`
- values: `IN_ROI` / `OUT_ROI`

## 2) Shared recording config
- Copy `grant/configs/grant_recording_config.example.json` to a per-recording config file.
- Update recording paths once, then use the same config for both run and post-analysis notebooks.

## 3) Probe-specific brain-region defaults
The default config now includes persistent probe/region assignments:
- A → NP2.0 Simplex Lobule & Interposed Nucleus
- B → NP1.0 Pontine Nuclei
- C → NP2.0 Motor Cortex
- D → NP2.0 Ventral Anterior Lateral complex of the thalamus
- E → NP1.0 Substantia Nigra (SNR)
- F → NP1.0 Reticular Nucleus

You can add per-probe / per-mode parameter overrides in the same config (`probe_param_overrides`, `mode_param_overrides`).

## 4) NP2.0 (4-shank, custom channel map) notes
For non-default channel maps:
1. Make sure `structure.oebin` in the config points to the matching recording.
2. Set probe stream names in `probe_stream_names` so each probe points to the right Open Ephys stream.
3. If channel counts differ from defaults, set `nChannels` / `nSyncChannels` in `probe_param_overrides`.
4. Keep NP2 rerun-specific waveform/quality threshold overrides in `mode_param_overrides.np20_rerun`.

### Why custom channel maps can affect Bombcell
- Bombcell quality metrics depend on unit waveforms and unit location on the probe (`maxChannels`, `channel_positions`).
- If Kilosort + Open Ephys metadata are aligned to the same custom map, Bombcell should work normally (it uses those outputs/metadata directly).
- If map metadata is mismatched (wrong stream, wrong `structure.oebin`, wrong channel counts), channel geometry and waveform extraction can be wrong, which can shift ROI labels and quality classification.

### Practical NP2.0 optimization checks (A/C/D)
1. Keep map provenance together per probe/run: NeuroCarto export (`.imro`/`.json`), Open Ephys stream, Kilosort folder.
2. Confirm each probe path in config resolves to the intended stream (`probe_stream_names`) and recording metadata (`structure_oebin_subpath`).
3. For each NP2.0 probe with custom map, set probe-specific `nChannels` / `nSyncChannels` in `probe_param_overrides` when they differ.
4. Use `mode_param_overrides.np20_rerun` for conservative waveform-shape thresholds on custom layouts, then compare unit-type counts in exported summaries before/after.
5. Keep per-probe ROI (`probe_recording_roi`) updated so `cluster_bc_roiLabel.tsv` and post-analysis ROI labels reflect the true sampled depth for that custom layout.

## 5) Suggested maintenance checks in the broader repo
- Keep `py_bombcell` and `matlab` parameter choices aligned for equivalent experiments.
- Preserve one exported summary per run (`batch_summary.csv`) for traceable reruns.
- Keep config files outside notebooks to avoid hidden path drift between collaborators.
