# Using BombCell with NP2.0 (4-shank) custom channel maps

This note summarizes what matters when you use NP2.0 probes with **non-default channel maps** (for example custom A/C or A/D layouts generated in NeuroCarto and passed to Open Ephys + Kilosort4).

## Short answer

If Kilosort output is consistent with your custom map, BombCell should usually work without extra changes because it reads geometry directly from Kilosort outputs (`channel_positions.npy`).

## What BombCell already uses from Kilosort/Open Ephys

- BombCell loads `channel_positions.npy` directly from the Kilosort folder and uses it as the source of per-channel geometry.
- For Open Ephys metadata, BombCell reads `.oebin` and uses `bitVolts` scaling for raw amplitudes.
- Probe gain defaults are handled for NP2 probe types when reading SpikeGLX metadata.

## Why custom maps can affect BombCell results

Many BombCell metrics are insensitive to geometry (e.g., refractory period violations, spike counts, amplitude statistics from the peak channel), but some parts are geometry-dependent:

1. **Spatial decay metrics**
   - Spatial decay assumes enough nearby channels exist in a local column.
   - Current implementation uses fixed spatial constants (e.g., `CHANNEL_TOLERANCE = 33`) and minimum nearby-channel counts.
   - If your custom map is sparse/interleaved across shanks, spatial decay can become unstable or disabled.

2. **Waveform neighborhood plotting / nearest-channel selection**
   - Nearby channels are selected based on simple x/y distance logic.
   - Unusual inter-shank layouts can pick less-ideal neighbors for visualization or local waveform summaries.

3. **Distance metrics from PCs (`nChannelsIsoDist`)**
   - Isolation/distance metrics use only a small number of nearby channels (default 4).
   - For unusual layouts this may under-sample the true local neighborhood for some units.

## Practical recommendations (no code changes required)

1. **Ensure Kilosort geometry is correct first**
   - Verify `channel_positions.npy` and `channel_map.npy` correspond exactly to your NeuroCarto layout used at sort time.
   - If this is wrong, BombCell cannot recover correct geometry later.

2. **Treat spatial decay as optional for sparse custom maps**
   - If channels are not dense in local columns, set `computeSpatialDecay = False` (Python) / `0` (MATLAB), or interpret this metric cautiously.

3. **Tune distance-metric neighborhood size**
   - Consider increasing `nChannelsIsoDist` above 4 for custom maps that spread neighboring informative channels farther apart.

4. **Use GUI + metric sanity checks on a small subset**
   - Compare a handful of units across default vs custom layouts to confirm max channel assignment and waveform neighborhood look sensible.

5. **Keep metadata-driven recording parameters**
   - Let BombCell read sample rate/channel counts from metadata where possible; avoid hardcoded mismatches.


## Probe-specific `nChannelsIsoDist` starting points (for your A/C/D patterns)

Given your channel patterns:

- **Probe A** (`ON,OFF,OFF,OFF` interleaving per column, inverted partner column): this is the sparsest local sampling. Start with **8** (reasonable test range: **8–12**).
- **Probe C** (`ON,OFF` interleaving per column, inverted partner column): moderate local sparsity. Start with **6** (test range: **6–8**).
- **Probe D** (contiguous ON block on shank): densest local neighborhood. Default **4** is usually fine (test range: **4–6**).

Rationale: `nChannelsIsoDist` controls how many nearby channels contribute to distance metrics. Sparser effective local sampling generally benefits from a larger neighborhood so the metric is not dominated by too few channels.

## Suggested future improvements to BombCell

If you want to improve robustness for non-default maps, the following would help:

1. **Adaptive geometry-aware neighbor selection**
   - Replace fixed x-thresholds with k-nearest-neighbor selection in Euclidean space (or graph adjacency from map).

2. **Per-layout spatial-decay eligibility checks**
   - Detect whether enough channels exist around each unit before computing spatial decay and annotate confidence.

3. **Expose geometry diagnostics**
   - Add a summary report (nearest-neighbor distances, channels-per-column, shank coverage) before metric computation.

4. **Shank-aware defaults**
   - Auto-tune `nChannelsIsoDist` and spatial-decay fit channel count from channel-position statistics.

## Bottom line

A custom NP2 channel map does **not inherently reduce BombCell quality**. It matters only insofar as geometry-dependent calculations assume local dense neighborhoods that your map may or may not preserve. The most important requirement is strict consistency of geometry across acquisition, sorting, and BombCell input files.
