# Building `grant_recording_config.json`

This guide explains the structure used by:

- `grant/running_BC/run_bombcell_unified.py`
- `grant/grant_config.py`

Use it to set:

- recording paths,
- single-probe parameter overrides,
- batch-mode parameter overrides,
- and "use Bombcell defaults" behavior.

---

## 1) Minimal required keys

At minimum, set:

```json
{
  "recording_name": "YourRecordingFolderName",
  "recordings_root": "H:/Grant/Neuropixels/Kilosort_Recordings"
}
```

Everything else is optional.

If optional keys are omitted, loader defaults in `grant/grant_config.py` are used.

---

## 2) Recommended starter workflow

1. Copy `grant_recording_config.example.json` to a new file (for your recording).
2. Edit `recording_name` and `recordings_root`.
3. Run once with no parameter overrides.
4. Add only the overrides you need.

---

## 3) How parameter overrides are read

Bombcell starts from `bc.get_default_parameters(...)` and then applies config overrides.

Current precedence (later items win if the same key is set multiple times):

1. `mode_param_overrides.<mode>.all`
2. `mode_param_overrides.<mode>.probes.<PROBE>`
3. `probe_param_overrides.<PROBE>.all_modes`
4. `probe_param_overrides.<PROBE>.modes.<mode>`

So the most specific place is:

- `probe_param_overrides.<PROBE>.modes.<mode>`

---

## 4) Single-probe settings

For `--mode single_probe --target-probe B`, use either:

- `probe_param_overrides.B.all_modes` (applies to B in every mode), and/or
- `probe_param_overrides.B.modes.single_probe` (only when mode is `single_probe`).

Example:

```json
{
  "probe_param_overrides": {
    "B": {
      "all_modes": {
        "minPresenceRatio": 0.6
      },
      "modes": {
        "single_probe": {
          "maxRPVviolations": 0.2,
          "presenceRatioBinSize": 120
        }
      }
    }
  }
}
```

---

## 5) Batch-mode settings

For `--mode batch`, set keys under `mode_param_overrides.batch`.

You can set:

- values for all probes in batch mode: `mode_param_overrides.batch.all`
- per-probe values only in batch mode: `mode_param_overrides.batch.probes.<PROBE>`

Example:

```json
{
  "mode_param_overrides": {
    "batch": {
      "all": {
        "computeTimeChunks": true
      },
      "probes": {
        "A": {
          "deltaTimeChunk": 360
        },
        "C": {
          "maxWvBaselineFraction": 0.5
        }
      }
    }
  }
}
```

---

## 6) Use default Bombcell parameters

To use Bombcell defaults, do **not** set an override for that parameter.

Simplest default-only config:

```json
{
  "recording_name": "YourRecordingFolderName",
  "recordings_root": "H:/Grant/Neuropixels/Kilosort_Recordings",
  "probe_param_overrides": {},
  "mode_param_overrides": {}
}
```

You can also omit `probe_param_overrides` and `mode_param_overrides` entirely.

---

## 7) Full example skeleton

```json
{
  "recording_name": "Reach15_20260201_session007_NP_Recording_Number02_2026-02-01_18-25-00",
  "recordings_root": "H:/Grant/Neuropixels/Kilosort_Recordings",
  "open_ephys_continuous_subpath": "Record Node 103/experiment1/recording1/continuous",
  "structure_oebin_subpath": "Record Node 103/experiment1/recording1/structure.oebin",
  "probe_stream_names": {
    "A": "Neuropix-PXI-100.ProbeA",
    "B": "Neuropix-PXI-100.ProbeB-AP",
    "C": "Neuropix-PXI-100.ProbeC",
    "D": "Neuropix-PXI-100.ProbeD",
    "E": "Neuropix-PXI-100.ProbeE-AP",
    "F": "Neuropix-PXI-100.ProbeF-AP"
  },
  "np20_probes": ["A", "C", "D"],
  "probe_recording_roi": {
    "A": 3450,
    "B": 950,
    "C": 1800,
    "D": 1400,
    "E": 800,
    "F": 1120
  },
  "mode_param_overrides": {},
  "probe_param_overrides": {}
}
```

---

## 8) Run commands

```bash
python grant/running_BC/run_bombcell_unified.py --config grant/configs/grant_recording_config.json --mode batch
python grant/running_BC/run_bombcell_unified.py --config grant/configs/grant_recording_config.json --mode single_probe --target-probe B
python grant/running_BC/run_bombcell_unified.py --config grant/configs/grant_recording_config.json --mode np20_rerun
```
