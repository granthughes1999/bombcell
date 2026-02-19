# Classification Reason Export - Documentation Index

This directory contains a new notebook for exporting Bombcell classification reasons to Phy.

## Main Files

### 📓 Notebook
- **[export_classification_reason_to_phy.ipynb](export_classification_reason_to_phy.ipynb)** - The main notebook to run

### 📖 Documentation
1. **[QUICKSTART_classification_reason.md](QUICKSTART_classification_reason.md)** - Start here! Quick guide with visual workflow
2. **[README_export_classification_reason.md](README_export_classification_reason.md)** - Comprehensive documentation
3. **[EXAMPLE_OUTPUT.md](EXAMPLE_OUTPUT.md)** - Example output and what to expect

### 🧪 Testing
- **[test_notebook_logic.py](test_notebook_logic.py)** - Validation script (optional, for developers)

## Quick Start

1. Open `export_classification_reason_to_phy.ipynb`
2. Set your configuration:
   ```python
   CONFIG_FILE = r'C:\...\grant_recording_config.json'
   RUN_MODE = 'single_probe'
   TARGET_PROBE = 'E'
   ```
3. Run all cells
4. Open your data in Phy - you'll see a new `bc_classificationReason` column!

## What This Does

Adds a new column to Phy's cluster view showing **why** each unit was classified as GOOD, NOISE, MUA, or NON-SOMA:

- ✅ **GOOD**: `GOOD: passed all thresholds`
- ❌ **NOISE**: `NOISE: scndPeakToTroughRatio>maxScndPeakToTroughRatio_noise`
- ❌ **MUA**: `MUA: fractionRPVs_estimatedTauR>maxRPVviolations`
- ❌ **NON-SOMA**: `NON-SOMA: mainPeakToTroughRatio>maxMainPeakToTroughRatio_nonSomatic`

## Workflow

```
Bombcell Results → Notebook → TSV File → Phy Column ✨
```

## Read Next

- **New users**: Start with [QUICKSTART_classification_reason.md](QUICKSTART_classification_reason.md)
- **Detailed info**: See [README_export_classification_reason.md](README_export_classification_reason.md)
- **Want to see examples**: Check [EXAMPLE_OUTPUT.md](EXAMPLE_OUTPUT.md)

## Related Notebooks

- **[BC_classification_reason_audit.ipynb](BC_classification_reason_audit.ipynb)** - Detailed auditing with plots and ALL reasons (for analysis)
- **[export_classification_reason_to_phy.ipynb](export_classification_reason_to_phy.ipynb)** - Quick export of MAIN reason (for Phy usage) ← You are here

## Questions?

See the comprehensive [README](README_export_classification_reason.md) for troubleshooting and advanced usage.
