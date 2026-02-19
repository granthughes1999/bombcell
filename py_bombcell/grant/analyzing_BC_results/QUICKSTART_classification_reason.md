# Classification Reason Export Workflow

## Quick Start Guide

### Step 1: Run Bombcell Analysis
First, ensure you have run Bombcell analysis on your data:
```python
# This creates quality_metrics, param, and unit classifications
bc.run_bombcell(ks_dir, save_path, param)
```

### Step 2: Run the Export Notebook
Open and run `export_classification_reason_to_phy.ipynb`:

```
┌─────────────────────────────────────────────────────────┐
│  export_classification_reason_to_phy.ipynb             │
│                                                         │
│  1. Configure (RUN_MODE, TARGET_PROBE, etc.)          │
│  2. Load Bombcell results                             │
│  3. Extract classification reasons                     │
│  4. Export TSV file                                    │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  cluster_bc_classificationReason.tsv                   │
│  ┌─────────────┬────────────────────────────────────┐  │
│  │ cluster_id  │ bc_classificationReason           │  │
│  ├─────────────┼────────────────────────────────────┤  │
│  │ 0           │ MUA: fractionRPVs_...>maxRPVviol  │  │
│  │ 1           │ NOISE: scndPeakToTroughRatio>max  │  │
│  │ 2           │ GOOD: passed all thresholds       │  │
│  │ 3           │ NON-SOMA: mainPeakToTroughRatio>  │  │
│  └─────────────┴────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  Open in Phy                                           │
│  ┌───────────────────────────────────────────────────┐ │
│  │ Cluster View                                      │ │
│  │ ┌──────┬──────────┬──────────────────────────┐   │ │
│  │ │ ID   │ Type     │ bc_classificationReason  │   │ │
│  │ ├──────┼──────────┼──────────────────────────┤   │ │
│  │ │ 0    │ MUA      │ MUA: fractionRPVs_...    │   │ │
│  │ │ 1    │ NOISE    │ NOISE: scndPeakToTrough  │   │ │
│  │ │ 2    │ GOOD     │ GOOD: passed all thresh  │   │ │
│  │ │ 3    │ NON-SOMA │ NON-SOMA: mainPeakToT... │   │ │
│  │ └──────┴──────────┴──────────────────────────┘   │ │
│  │                                                   │ │
│  │  You can now sort/filter by classification!      │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Step 3: View in Phy
The new column appears automatically in Phy's cluster view!

## What Gets Exported

For each unit, the notebook determines the **main reason** for its classification:

### GOOD Units
✓ `GOOD: passed all thresholds`

### NOISE Units  
❌ One of:
- `NOISE: nPeaks>maxNPeaks`
- `NOISE: nTroughs>maxNTroughs`
- `NOISE: wvDuration<minWvDuration`
- `NOISE: baselineFlatness>maxWvBaselineFraction`
- `NOISE: scndPeakToTroughRatio>maxScndPeakToTroughRatio_noise`
- etc.

### MUA Units
❌ One of:
- `MUA: fractionRPVs_estimatedTauR>maxRPVviolations` ← Most common
- `MUA: presenceRatio<minPresenceRatio`
- `MUA: percentageSpikesMissing_gaussian>maxPercSpikesMissing`
- `MUA: nSpikes<minNumSpikes`
- etc.

### NON-SOMA Units
❌ One of:
- `NON-SOMA: mainPeakToTroughRatio>maxMainPeakToTroughRatio_nonSomatic`
- `NON-SOMA: troughToPeak2Ratio<minTroughToPeak2Ratio_nonSomatic`
- `NON-SOMA: mainTrough_width<minWidthMainTrough_nonSomatic`
- etc.

## Comparison with Existing Notebooks

| Notebook | Purpose | Output |
|----------|---------|--------|
| `BC_classification_reason_audit.ipynb` | **Detailed auditing** with plots and ALL reasons | DataFrame in memory |
| `export_classification_reason_to_phy.ipynb` | **Quick export** of MAIN reason for Phy | TSV file for Phy |

Use the audit notebook for deep analysis, use the export notebook for day-to-day Phy usage.

## File Locations

```
your_kilosort_directory/
├── spike_times.npy
├── spike_clusters.npy
├── templates.npy
├── cluster_bc_unitType.tsv          ← Unit type (GOOD/NOISE/MUA/NON-SOMA)
├── cluster_bc_classificationReason.tsv ← NEW! Main reason ✨
├── cluster_bc_roiLabel.tsv          ← ROI label (if configured)
└── bombcell/                        ← Bombcell results directory
    ├── templates._bc_qMetrics.csv
    └── _bc_parameters._bc_qMetrics.parquet
```

## Tips

1. **Run after any Bombcell re-analysis** to update the reasons in Phy
2. **Use VERBOSE=True** in the notebook to see detailed breakdowns
3. **Sort by reason in Phy** to group similar failure modes together
4. **Filter by specific reasons** to focus on particular quality issues

## Example Session

```python
# In the notebook:
CONFIG_FILE = r'C:\...\grant_recording_config.json'
RUN_MODE = 'single_probe'
TARGET_PROBE = 'E'
VERBOSE = True

# Run all cells...

# Output:
# Loaded 1316 units
# 
# Label distribution:
# MUA         764
# NON-SOMA    286
# NOISE       247
# GOOD         19
#
# ✓ Successfully exported classification reasons to:
#   H:\...\kilosort4_E\cluster_bc_classificationReason.tsv
```

Then in Phy, you'll see the new column and can immediately understand why each unit was classified the way it was!
