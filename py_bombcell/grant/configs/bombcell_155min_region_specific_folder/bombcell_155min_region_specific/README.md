# bombcell_155min_region_specific

Region- and probe-type–specific Bombcell parameter presets for 155-minute Open Ephys Neuropixels sessions.

## Files
- `params_155min_region_specific.py`: BASE preset + per-probe overrides + `get_params()`
- `session_config_155min_region_specific.json`: updated session config with per-probe overrides in the same schema you provided

## Use in single-probe mode
```python
from bombcell_155min_region_specific import get_params

params = get_params("C", mode="single_probe")
```

## Use in batch mode (multi-probe)
```python
from bombcell_155min_region_specific import get_params

for probe in ["A","B","C","D","E","F"]:
    params = get_params(probe, mode="batch")
```

## Notes
- `mode` only changes params if you add entries to `MODE_OVERRIDES`. Thresholding is intentionally identical across modes.
- Open Ephys paths/stream names remain in the session JSON; your pipeline should inject `ephysMetaFile/rawFile/nChannels/nSyncChannels`
  at runtime as you already do.
