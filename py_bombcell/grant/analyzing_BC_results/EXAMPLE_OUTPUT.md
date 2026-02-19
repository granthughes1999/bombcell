# Example Output

This document shows what the output of `export_classification_reason_to_phy.ipynb` looks like.

## Console Output Example

```
Kilosort directory: H:\Grant\...\bombcell\bombcell_single_probe\kilosort4_E
Bombcell save path: H:\Grant\...\bombcell\bombcell_single_probe\kilosort4_E\bombcell

TSV file will be saved to: H:\Grant\...\bombcell\bombcell_single_probe\kilosort4_E\cluster_bc_classificationReason.tsv

Loaded 1316 units

Label distribution:
MUA         764
NON-SOMA    286
NOISE       247
GOOD         19
Name: count, dtype: int64

Defined classification rules:
  NOISE: 6 criteria
  MUA: 4 criteria
  NON-SOMA: 5 criteria

Classification reasons extracted!

Example reasons (first 5 units):
  Unit 0 (MUA): MUA: fractionRPVs_estimatedTauR>maxRPVviolations
  Unit 1 (MUA): MUA: fractionRPVs_estimatedTauR>maxRPVviolations
  Unit 2 (NOISE): NOISE: scndPeakToTroughRatio>maxScndPeakToTroughRatio_noise
  Unit 3 (MUA): MUA: fractionRPVs_estimatedTauR>maxRPVviolations
  Unit 4 (GOOD): GOOD: passed all thresholds

Main reason distribution:
MUA: fractionRPVs_estimatedTauR>maxRPVviolations                    512
NOISE: scndPeakToTroughRatio>maxScndPeakToTroughRatio_noise        198
NON-SOMA: mainPeakToTroughRatio>maxMainPeakToTroughRatio_nonSomatic 186
MUA: percentageSpikesMissing_gaussian>maxPercSpikesMissing          98
NON-SOMA: troughToPeak2Ratio<minTroughToPeak2Ratio_nonSomatic       71
NOISE: wvDuration>maxWvDuration                                     29
NON-SOMA: peak1ToPeak2Ratio>maxPeak1ToPeak2Ratio_nonSomatic         19
GOOD: passed all thresholds                                         19
...

✓ Successfully exported classification reasons to:
  H:\Grant\...\bombcell\bombcell_single_probe\kilosort4_E\cluster_bc_classificationReason.tsv

Exported 1316 units

To view in Phy:
  1. Open your data in Phy
  2. Look for the "bc_classificationReason" column in the cluster view
  3. You can sort and filter by this column to explore classification reasons

Preview of exported TSV file (first 10 rows):
   cluster_id                             bc_classificationReason
0           0  MUA: fractionRPVs_estimatedTauR>maxRPVviolations
1           1  MUA: fractionRPVs_estimatedTauR>maxRPVviolations
2           2  NOISE: scndPeakToTroughRatio>maxScndPeakToTrou...
3           3  MUA: fractionRPVs_estimatedTauR>maxRPVviolations
4           4                      GOOD: passed all thresholds
5           5  MUA: fractionRPVs_estimatedTauR>maxRPVviolations
6           6  MUA: fractionRPVs_estimatedTauR>maxRPVviolations
7           7  NON-SOMA: mainPeakToTroughRatio>maxMainPeakToT...
8           8  MUA: fractionRPVs_estimatedTauR>maxRPVviolations
9           9  MUA: percentageSpikesMissing_gaussian>maxPercS...
```

## Detailed Output with VERBOSE=True

When you set `VERBOSE = True`, you also get detailed breakdowns:

```
================================================================================
DETAILED VIEW: Example units for each classification
================================================================================

GOOD units (showing up to 3 examples):
  Cluster 4:
    Main: GOOD: passed all thresholds

  Cluster 42:
    Main: GOOD: passed all thresholds

  Cluster 89:
    Main: GOOD: passed all thresholds


NOISE units (showing up to 3 examples):
  Cluster 2:
    Main: NOISE: scndPeakToTroughRatio>maxScndPeakToTroughRatio_noise

  Cluster 10:
    Main: NOISE: scndPeakToTroughRatio>maxScndPeakToTroughRatio_noise

  Cluster 13:
    Main: NOISE: scndPeakToTroughRatio>maxScndPeakToTroughRatio_noise


MUA units (showing up to 3 examples):
  Cluster 0:
    Main: MUA: fractionRPVs_estimatedTauR>maxRPVviolations

  Cluster 1:
    Main: MUA: fractionRPVs_estimatedTauR>maxRPVviolations

  Cluster 3:
    Main: MUA: fractionRPVs_estimatedTauR>maxRPVviolations


NON-SOMA units (showing up to 3 examples):
  Cluster 7:
    Main: NON-SOMA: mainPeakToTroughRatio>maxMainPeakToTroughRatio_nonSomatic

  Cluster 11:
    Main: NON-SOMA: mainPeakToTroughRatio>maxMainPeakToTroughRatio_nonSomatic

  Cluster 14:
    Main: NON-SOMA: mainPeakToTroughRatio>maxMainPeakToTroughRatio_nonSomatic
```

## TSV File Format

The exported `cluster_bc_classificationReason.tsv` file looks like this:

```tsv
cluster_id	bc_classificationReason
0	MUA: fractionRPVs_estimatedTauR>maxRPVviolations
1	MUA: fractionRPVs_estimatedTauR>maxRPVviolations
2	NOISE: scndPeakToTroughRatio>maxScndPeakToTroughRatio_noise
3	MUA: fractionRPVs_estimatedTauR>maxRPVviolations
4	GOOD: passed all thresholds
5	MUA: fractionRPVs_estimatedTauR>maxRPVviolations
6	MUA: fractionRPVs_estimatedTauR>maxRPVviolations
7	NON-SOMA: mainPeakToTroughRatio>maxMainPeakToTroughRatio_nonSomatic
8	MUA: fractionRPVs_estimatedTauR>maxRPVviolations
9	MUA: percentageSpikesMissing_gaussian>maxPercSpikesMissing
...
```

## How It Looks in Phy

When you open your data in Phy, the cluster view will now include a new column:

```
┌──────────┬─────────────┬──────────────────────────────────────────────────┐
│ Cluster  │ bc_unitType │ bc_classificationReason                         │
├──────────┼─────────────┼──────────────────────────────────────────────────┤
│ 0        │ MUA         │ MUA: fractionRPVs_estimatedTauR>maxRPVviolations│
│ 1        │ MUA         │ MUA: fractionRPVs_estimatedTauR>maxRPVviolations│
│ 2        │ NOISE       │ NOISE: scndPeakToTroughRatio>maxScndPeakToTrough│
│ 3        │ MUA         │ MUA: fractionRPVs_estimatedTauR>maxRPVviolations│
│ 4        │ GOOD        │ GOOD: passed all thresholds                      │
│ 5        │ MUA         │ MUA: fractionRPVs_estimatedTauR>maxRPVviolations│
│ 7        │ NON-SOMA    │ NON-SOMA: mainPeakToTroughRatio>maxMainPeakToTro│
│ 8        │ MUA         │ MUA: fractionRPVs_estimatedTauR>maxRPVviolations│
│ 9        │ MUA         │ MUA: percentageSpikesMissing_gaussian>maxPercSpi│
└──────────┴─────────────┴──────────────────────────────────────────────────┘
```

You can:
- **Click the column header** to sort by classification reason
- **Right-click the column** to filter by specific reasons
- **Select multiple units** with the same reason to review them together
- **Use Phy's search** to find units with specific failure criteria

## Common Classification Reasons

Based on typical Bombcell results, here are the most common reasons you'll see:

### Most Common MUA Reasons
1. `MUA: fractionRPVs_estimatedTauR>maxRPVviolations` (40-50% of MUA units)
   - Too many refractory period violations
   - Suggests contamination with other units

2. `MUA: percentageSpikesMissing_gaussian>maxPercSpikesMissing` (10-15%)
   - ISI distribution suggests missing spikes
   - Unit might be poorly isolated

3. `MUA: presenceRatio<minPresenceRatio` (5-10%)
   - Unit not present throughout recording
   - Might be drift or unstable recording

### Most Common NOISE Reasons
1. `NOISE: scndPeakToTroughRatio>maxScndPeakToTroughRatio_noise` (60-80%)
   - Waveform has unusual secondary peak
   - Typical of noise or artifacts

2. `NOISE: wvDuration>maxWvDuration` (10-20%)
   - Waveform is too wide
   - Not a typical neuronal spike

3. `NOISE: nPeaks>maxNPeaks` (5-10%)
   - Waveform has too many peaks
   - Likely multi-unit or artifact

### Most Common NON-SOMA Reasons
1. `NON-SOMA: mainPeakToTroughRatio>maxMainPeakToTroughRatio_nonSomatic` (50-70%)
   - Peak-to-trough ratio indicates axonal recording
   - Common for axon initial segment spikes

2. `NON-SOMA: troughToPeak2Ratio<minTroughToPeak2Ratio_nonSomatic` (15-25%)
   - Unusual trough-to-second-peak ratio
   - Characteristic of non-somatic recordings

3. `NON-SOMA: mainTrough_width<minWidthMainTrough_nonSomatic` (10-15%)
   - Main trough is too narrow
   - Typical of axonal recordings
