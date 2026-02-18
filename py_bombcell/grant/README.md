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

## 5) Suggested maintenance checks in the broader repo
- Keep `py_bombcell` and `matlab` parameter choices aligned for equivalent experiments.
- Preserve one exported summary per run (`batch_summary.csv`) for traceable reruns.
- Keep config files outside notebooks to avoid hidden path drift between collaborators.
