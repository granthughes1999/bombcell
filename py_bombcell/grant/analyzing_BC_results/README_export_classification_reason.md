# Export Classification Reason to Phy

## Overview

This notebook (`export_classification_reason_to_phy.ipynb`) extracts the main classification reason for each unit from Bombcell results and exports it as a TSV file that can be viewed in Phy's cluster view tab.

## What It Does

The notebook:
1. Loads Bombcell quality metrics and parameters
2. Analyzes why each unit was classified as GOOD, NOISE, MUA, or NON-SOMA
3. Extracts the **main (first) reason** for each classification
4. Exports this information as a `cluster_bc_classificationReason.tsv` file
5. Places the file in your Kilosort directory for Phy to read

## Why This Is Useful

When reviewing units in Phy, you can now see:
- **GOOD units**: "GOOD: passed all thresholds"
- **NOISE units**: Which specific criterion failed (e.g., "NOISE: nPeaks>maxNPeaks")
- **MUA units**: Which quality metric was below threshold (e.g., "MUA: fractionRPVs_estimatedTauR>maxRPVviolations")
- **NON-SOMA units**: Which waveform feature indicated non-somatic activity

This makes it much easier to understand and audit Bombcell's classification decisions directly in Phy's interface.

## Usage

### 1. Configure the Notebook

Open `export_classification_reason_to_phy.ipynb` and set these parameters in the first code cell:

```python
CONFIG_FILE = r'C:\Users\user\Documents\github\bombcell\py_bombcell\grant\configs\grant_recording_config.json'
RUN_MODE = 'single_probe'  # 'batch', 'single_probe', or 'np20_rerun'
TARGET_PROBE = 'E'  # Only used for single_probe mode
VERBOSE = True  # Set to False for less output
```

### 2. Run the Notebook

Execute all cells in order. The notebook will:
- Load your Bombcell results
- Extract classification reasons
- Show a summary of reasons by type
- Export the TSV file

### 3. View in Phy

1. Open your data in Phy (from the Kilosort directory)
2. Look for the **bc_classificationReason** column in the cluster view
3. Sort and filter by this column to explore classification reasons

## Output Format

The notebook creates a TSV file with this structure:

```
cluster_id	bc_classificationReason
0	MUA: fractionRPVs_estimatedTauR>maxRPVviolations
1	NOISE: scndPeakToTroughRatio>maxScndPeakToTroughRatio_noise
2	GOOD: passed all thresholds
3	NON-SOMA: mainPeakToTroughRatio>maxMainPeakToTroughRatio_nonSomatic
...
```

## Classification Reasons

### GOOD Units
- `GOOD: passed all thresholds` - Unit passed all NOISE, MUA, and NON-SOMA checks

### NOISE Units
Possible reasons include:
- `NOISE: nPeaks>maxNPeaks` - Too many peaks in waveform
- `NOISE: nTroughs>maxNTroughs` - Too many troughs in waveform
- `NOISE: wvDuration<minWvDuration` - Waveform too short
- `NOISE: wvDuration>maxWvDuration` - Waveform too long
- `NOISE: baselineFlatness>maxWvBaselineFraction` - Baseline not flat enough
- `NOISE: scndPeakToTroughRatio>maxScndPeakToTroughRatio_noise` - Secondary peak too large
- `NOISE: spatialDecaySlope<minSpatialDecaySlope` - Spatial decay too shallow (if computed)

### MUA Units
Possible reasons include:
- `MUA: percentageSpikesMissing_gaussian>maxPercSpikesMissing` - Too many spikes missing
- `MUA: nSpikes<minNumSpikes` - Not enough spikes detected
- `MUA: fractionRPVs_estimatedTauR>maxRPVviolations` - Too many refractory period violations
- `MUA: presenceRatio<minPresenceRatio` - Unit not present enough throughout recording
- `MUA: rawAmplitude<minAmplitude` - Amplitude too low (if raw waveforms extracted)
- `MUA: signalToNoiseRatio<minSNR` - SNR too low (if raw waveforms extracted)
- `MUA: maxDriftEstimate>maxDrift` - Too much drift (if computed)
- `MUA: isolationDistance<isoDmin` - Not well isolated (if computed)
- `MUA: Lratio>lratioMax` - L-ratio too high (if computed)

### NON-SOMA Units
Possible reasons include:
- `NON-SOMA: troughToPeak2Ratio<minTroughToPeak2Ratio_nonSomatic` - Unusual trough-to-peak ratio
- `NON-SOMA: mainPeak_before_width<minWidthFirstPeak_nonSomatic` - First peak too narrow
- `NON-SOMA: mainTrough_width<minWidthMainTrough_nonSomatic` - Main trough too narrow
- `NON-SOMA: peak1ToPeak2Ratio>maxPeak1ToPeak2Ratio_nonSomatic` - Peak ratio indicates non-somatic
- `NON-SOMA: mainPeakToTroughRatio>maxMainPeakToTroughRatio_nonSomatic` - Peak-to-trough ratio indicates non-somatic

## Relation to BC_classification_reason_audit.ipynb

This notebook is based on the logic from `BC_classification_reason_audit.ipynb`, but:
- Focuses on exporting the **main reason** (first criterion that failed) rather than all reasons
- Outputs to a Phy-compatible TSV file
- Is streamlined for regular use rather than detailed auditing
- Can be run repeatedly to update the Phy column after re-running Bombcell

For detailed auditing with plots and all reasons listed, use `BC_classification_reason_audit.ipynb`.

## Requirements

- Bombcell results must already be computed
- Python packages: `bombcell`, `numpy`, `pandas`, `pathlib`
- Grant's configuration system (for `load_grant_config`)

## Troubleshooting

### "No module named 'grant_config'"
Make sure you're running from the `analyzing_BC_results` directory, or adjust the path in the notebook.

### "Cannot find Bombcell results"
Check that:
1. You've run Bombcell analysis first
2. The paths in your config file are correct
3. The `RUN_MODE` and `TARGET_PROBE` match your analysis

### "Column not found" errors
This can happen if certain metrics weren't computed. The notebook handles this gracefully by using `col()` helper function that returns NaN for missing columns.

## Example Output

```
Loaded 1316 units

Label distribution:
MUA         764
NON-SOMA    286
NOISE       247
GOOD         19

Main reason distribution:
MUA: fractionRPVs_estimatedTauR>maxRPVviolations           512
NOISE: scndPeakToTroughRatio>maxScndPeakToTroughRatio_noise 198
NON-SOMA: mainPeakToTroughRatio>maxMainPeakToTroughRatio_nonSomatic 186
MUA: percentageSpikesMissing_gaussian>maxPercSpikesMissing    98
...

✓ Successfully exported classification reasons to:
  /path/to/kilosort4_E/cluster_bc_classificationReason.tsv
```

## See Also

- `BC_classification_reason_audit.ipynb` - Detailed classification auditing with plots
- `cluster_bc_unitType.tsv` - The main unit type classification (GOOD/NOISE/MUA/NON-SOMA)
- `cluster_bc_roiLabel.tsv` - ROI labels (IN_ROI/OUT_ROI) if configured
