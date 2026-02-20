# BombCell Comprehensive Jupyter Notebooks

This directory contains two comprehensive Jupyter notebooks that demonstrate all plotting capabilities and parameter tuning for BombCell.

## 📚 Available Notebooks

### 1. BC_comprehensive_plotting_guide.ipynb
**Purpose:** Complete guide to all plotting and visualization capabilities in BombCell.

**Contents:**
- Setup & data loading (with JSON session support)
- Summary plots (waveforms overlay, histograms, upset plots)
- Individual unit quality plots (10+ plot types)
- Cell type classification plots (cortex & striatum)
- Interactive GUI demonstration
- Export & summary functionality
- Quick reference appendix

**Who should use this:**
- First-time BombCell users learning available visualizations
- Users wanting to generate publication-quality figures
- Anyone needing to inspect individual unit quality
- Users integrating BombCell with Phy

**Total:** 62 cells with detailed documentation for each plot type

---

### 2. BC_parameter_effects_guide.ipynb
**Purpose:** Understand how parameter changes affect unit classification.

**Contents:**
- Parameter sweep framework with visualization
- Waveform-based parameters (noise classification)
- Non-somatic parameters (axonal detection)
- Amplitude & SNR parameters
- Spike train quality parameters
- Parameter selection guidelines
- Common parameter combinations
- Complete reference table

**Who should use this:**
- Users fine-tuning BombCell for their specific dataset
- Anyone wanting to understand parameter effects
- Users with challenging recordings (noisy, drift, etc.)
- Researchers optimizing for specific brain regions

**Total:** 43 cells with parameter sweep demonstrations

---

## 🚀 Getting Started

### Prerequisites

Install BombCell:
```bash
conda create -n bombcell python=3.11
conda activate bombcell
pip install uv
uv pip install bombcell
```

Or install dev version:
```bash
git clone https://github.com/Julie-Fabre/bombcell.git
cd bombcell/py_bombcell
uv pip install -e .
```

### Quick Start

1. **Open either notebook in Jupyter:**
```bash
jupyter notebook BC_comprehensive_plotting_guide.ipynb
```

2. **Update the paths in Section 1:**
```python
# Set your Kilosort directory
ks_dir = "path/to/your/kilosort/directory"
```

3. **Run the cells sequentially**

---

## 📖 What Each Notebook Covers

### Comprehensive Plotting Guide - Detailed Breakdown

**Section 1: Setup & Data Loading**
- Installation instructions
- Import libraries
- Load from Kilosort directory or JSON files
- Run BombCell analysis
- Load ephys data

**Section 2: Summary Plots**
- Waveforms overlay (4-5 categories)
- Quality metrics histograms (17 metrics)
- UpSet plots (metric interconnections)

**Section 3: Individual Unit Plots**
- Template waveform (multi-channel)
- Raw waveform overlay
- Autocorrelogram (ACG)
- Amplitude histogram with Gaussian fit
- Spatial decay plot
- Amplitude over time (drift)
- Presence ratio over time
- Unit location on probe

**Section 4: Cell Type Classification**
- Cortical cells (pyramidal/interneuron)
- Striatal cells (MSN/FSI/TAN/UIN)

**Section 5: Interactive GUI**
- Launch unit quality GUI
- Pre-compute data for fast loading

**Section 6: Summary & Export**
- Export results for Phy
- Create summary tables
- Final analysis summary

---

### Parameter Effects Guide - Detailed Breakdown

**Section 1: Setup**
- Import libraries
- Load session data
- Run baseline analysis
- Define helper functions

**Section 2: Waveform Parameters (Noise Classification)**
- Maximum peaks (maxNPeaks)
- Maximum troughs (maxNTroughs)
- Waveform duration (min/max)
- Baseline flatness
- Spatial decay slope

**Section 3: Non-Somatic Parameters**
- Trough to peak2 ratio
- Peak1 to peak2 ratio
- Main peak to trough ratio
- Width thresholds

**Section 4: Amplitude & SNR Parameters**
- Minimum amplitude
- Minimum SNR

**Section 5: Spike Train Quality Parameters**
- Refractory period violations
- Presence ratio
- Percentage spikes missing
- Minimum spike count

**Section 6: Summary & Recommendations**
- Guidelines by recording quality
- Guidelines by recording duration
- Guidelines by brain region
- Iterative tuning workflow
- Common parameter combinations

---

## 💡 Key Features

### Notebook #1 Features:
✅ Complete coverage of all 17 quality metrics  
✅ Every plot type demonstrated with examples  
✅ Clear documentation of data requirements  
✅ Instructions for enabling optional computations  
✅ Interactive GUI integration  
✅ Export functionality for Phy  
✅ Quick reference appendix  

### Notebook #2 Features:
✅ Visual parameter sweep framework  
✅ Each parameter tested across realistic ranges  
✅ Both count and percentage visualizations  
✅ Guidelines for different scenarios  
✅ Common parameter combinations tested  
✅ Complete reference table  
✅ Best practices and recommendations  

---

## 📊 Example Use Cases

### Use Case 1: First Analysis
1. Open **BC_comprehensive_plotting_guide.ipynb**
2. Follow sections 1-2 to run BombCell with defaults
3. Inspect summary plots
4. Use GUI to browse units

### Use Case 2: Parameter Optimization
1. Run baseline analysis with defaults
2. Open **BC_parameter_effects_guide.ipynb**
3. Test different parameter values
4. Choose optimal settings for your data

### Use Case 3: Publication Figures
1. Open **BC_comprehensive_plotting_guide.ipynb**
2. Run analysis with finalized parameters
3. Enable plot saving: `param["savePlots"] = True`
4. Generate all summary plots (Section 2)
5. Export results for Phy (Section 6)

### Use Case 4: Challenging Dataset
1. Open **BC_parameter_effects_guide.ipynb**
2. Try "Permissive" parameter set
3. Adjust individual parameters based on histograms
4. Validate with GUI inspection

---

## 🎯 Parameter Tuning Quick Reference

### High-Quality Recordings (Strict)
```python
param["minAmplitude"] = 50
param["minSNR"] = 6
param["maxRPVviolations"] = 0.05
param["maxPercSpikesMissing"] = 15
param["minPresenceRatio"] = 0.8
```

### Standard Recordings (Balanced - Default)
```python
# Use defaults - they work well!
param = bc.get_default_parameters(ks_dir)
```

### Noisy/Challenging Recordings (Permissive)
```python
param["minAmplitude"] = 30
param["minSNR"] = 4
param["maxRPVviolations"] = 0.15
param["maxPercSpikesMissing"] = 25
param["minPresenceRatio"] = 0.6
```

---

## 📈 Quality Metrics Reference

### 17 Computed Metrics

**Waveform-Based (Noise Classification):**
1. nPeaks - Number of peaks
2. nTroughs - Number of troughs
3. waveformBaselineFlatness - Baseline noise
4. waveformDuration_peakTrough - Duration (µs)
5. scndPeakToTroughRatio - Second peak size
6. spatialDecaySlope - Decay across channels

**Non-Somatic Classification:**
7. peak1ToPeak2Ratio - Peak balance
8. mainPeakToTroughRatio - Peak vs trough

**Amplitude & Noise:**
9. rawAmplitude - Spike amplitude (µV)
10. signalToNoiseRatio - SNR

**Spike Train Quality (MUA Classification):**
11. fractionRPVs_estimatedTauR - Refractory violations
12. nSpikes - Total spike count
13. presenceRatio - Time coverage
14. percentageSpikesMissing_gaussian - Estimated missing
15. maxDriftEstimate - Spatial drift (µm)

**Optional Distance Metrics:**
16. isolationDistance - Cluster isolation
17. Lratio - Contamination measure

---

## 🔧 Troubleshooting

### Problem: Raw waveforms not available
**Solution:**
```python
param["extractRaw"] = True
param["raw_data_file"] = "path/to/recording.bin"
```

### Problem: Drift metrics not computed
**Solution:**
```python
param["computeDrift"] = True
```

### Problem: Too few good units
**Solution:**
- Check histograms to see where units fail
- Consider relaxing relevant thresholds
- Use parameter effects notebook to find optimal values

### Problem: Too many noise/MUA units
**Solution:**
- Tighten quality thresholds
- Check recording quality
- Inspect borderline units with GUI

---

## 📚 Additional Resources

- **BombCell Wiki:** https://github.com/Julie-Fabre/bombcell/wiki
- **Paper:** Fabre et al. (2023) DOI: 10.5281/zenodo.8172821
- **Tutorial Video:** https://www.youtube.com/watch?v=CvXUtGzkXIY
- **Main Repository:** https://github.com/Julie-Fabre/bombcell
- **Issues/Questions:** https://github.com/Julie-Fabre/bombcell/issues

---

## 🤝 Contributing

If you find issues or have suggestions for improving these notebooks:
1. Open an issue on GitHub
2. Provide example data if possible
3. Describe expected vs. actual behavior

---

## 📝 Citation

If you use BombCell in your research, please cite:

> Julie M.J. Fabre, Enny H. van Beest, Andrew J. Peters, Matteo Carandini, & Kenneth D. Harris. (2023). 
> Bombcell: automated curation and cell classification of spike-sorted electrophysiology data. 
> Zenodo. https://doi.org/10.5281/zenodo.8172821

---

## 📄 License

These notebooks are part of the BombCell project and are licensed under GPLv3.

---

**Last Updated:** February 2025  
**BombCell Version:** Latest  
**Notebook Version:** 1.0
