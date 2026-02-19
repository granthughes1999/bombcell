# 🚀 BombCell Notebooks Quick Start

## Two Notebooks, Two Purposes

### 📊 Notebook #1: **BC_comprehensive_plotting_guide.ipynb**
**Use when:** You want to visualize your BombCell results

**What it does:**
- Shows ALL possible plots BombCell can create
- Demonstrates every quality metric visualization
- Provides interactive unit browsing
- Exports results for Phy

**5-Minute Start:**
```python
# 1. Update path (Cell 1.3)
ks_dir = "your/kilosort/directory"

# 2. Run BombCell (Cell 1.4)
param = bc.get_default_parameters(ks_dir)
qm, unit_type, unit_type_string = bc.run_bombcell(param)

# 3. Generate all plots (Cell 2.4)
bc.plot_summary_data(qm, template_waveforms, unit_type, unit_type_string, param)

# 4. Launch interactive GUI (Cell 5.1)
gui = bc.unit_quality_gui(ephys_data, qm, param, unit_type_string)
```

---

### 🎛️ Notebook #2: **BC_parameter_effects_guide.ipynb**
**Use when:** You want to optimize BombCell parameters for your data

**What it does:**
- Shows how each parameter affects classification
- Visualizes parameter sweeps with plots
- Provides guidelines for different scenarios
- Compares common parameter sets

**5-Minute Start:**
```python
# 1. Update path (Cell 1.2)
ks_dir = "your/kilosort/directory"

# 2. Run baseline (Cell 1.3)
baseline_qm, baseline_unit_type, baseline_unit_type_string = bc.run_bombcell(baseline_param)

# 3. Test a parameter (e.g., Cell 4.1)
param_values = [20, 30, 40, 50, 60]  # minAmplitude in µV
results = [run_with_param(baseline_param, "minAmplitude", val) for val in param_values]
plot_param_sweep(param_values, results, "minAmplitude", "µV")

# 4. Try common parameter sets (Cell 6.3)
# See comparison of Strict/Balanced/Permissive
```

---

## 📁 File Locations

```
bombcell/py_bombcell/demos/
├── BC_comprehensive_plotting_guide.ipynb    ← Notebook #1 (Plotting)
├── BC_parameter_effects_guide.ipynb         ← Notebook #2 (Parameters)
├── README_NOTEBOOKS.md                       ← Full documentation
└── QUICKSTART.md                             ← This file
```

---

## 🎯 Common Workflows

### Workflow 1: First-Time User
1. Open **BC_comprehensive_plotting_guide.ipynb**
2. Update your `ks_dir` path
3. Run Section 1 (Setup)
4. Run Section 2 (Summary Plots)
5. Browse units with GUI (Section 5)

---

### Workflow 2: Optimizing Parameters
1. Run BombCell with defaults
2. Look at histograms - which metrics are failing?
3. Open **BC_parameter_effects_guide.ipynb**
4. Test relevant parameter ranges
5. Choose optimal values
6. Re-run BombCell with new parameters

---

### Workflow 3: Publication Figures
1. Finalize parameters using Notebook #2
2. Open **BC_comprehensive_plotting_guide.ipynb**
3. Enable saving: `param["savePlots"] = True`
4. Run Section 2 to generate all summary plots
5. Individual plots in Section 3 for specific units
6. Figures saved to: `ks_dir/bombcell_plots/`

---

### Workflow 4: Challenging Dataset
1. Open **BC_parameter_effects_guide.ipynb**
2. Go to Section 6.3 (Common Parameter Sets)
3. Try "Permissive" parameter set
4. Check classification breakdown
5. Adjust specific parameters as needed
6. Validate with GUI in Notebook #1

---

## 🔍 Which Parameters to Adjust?

### If too many NOISE units:
Try relaxing:
- `maxNPeaks` (increase to 3-4)
- `maxWvDuration` (increase to 1300-1500 µs)
- `maxWvBaselineFraction` (increase to 0.4-0.5)

### If too many MUA units:
Try relaxing:
- `minAmplitude` (decrease to 30 µV)
- `minSNR` (decrease to 4)
- `maxRPVviolations` (increase to 0.15)
- `maxPercSpikesMissing` (increase to 25%)

### If too few good units overall:
Try "Permissive" parameter set from Notebook #2, Section 6.3

---

## 💡 Tips

**Tip 1: Start with defaults**
```python
param = bc.get_default_parameters(ks_dir)
# Defaults work well for most Neuropixels recordings
```

**Tip 2: Use histograms to diagnose**
Look at histogram plots (Notebook #1, Section 2.2) to see where units are failing specific metrics.

**Tip 3: Adjust one parameter at a time**
Use the parameter sweep framework in Notebook #2 to see isolated effects.

**Tip 4: Validate with GUI**
Always check borderline units manually with the interactive GUI.

**Tip 5: Document your choices**
Save your final parameters:
```python
import json
with open('final_parameters.json', 'w') as f:
    json.dump(param, f, indent=2)
```

---

## 📊 Plot Gallery

**From Notebook #1, you can generate:**

| Plot Type | Purpose | Section |
|-----------|---------|---------|
| Waveforms Overlay | Compare shapes by category | 2.1 |
| Histograms | See metric distributions | 2.2 |
| UpSet Plots | See metric interconnections | 2.3 |
| Template Waveforms | Inspect unit waveform | 3.1 |
| Raw Waveforms | See spike variability | 3.2 |
| Autocorrelograms | Check refractory period | 3.3 |
| Amplitude Histogram | Detect missing spikes | 3.4 |
| Spatial Decay | Somatic vs axonal | 3.5 |
| Amplitude Over Time | Monitor drift | 3.6 |
| Presence Ratio | Check stability | 3.7 |
| Probe Location | Spatial distribution | 3.8 |
| Cell Classification | Pyramidal/Interneuron | 4.2-4.3 |

---

## 🆘 Quick Troubleshooting

**Problem:** "Module not found: bombcell"
```bash
pip install bombcell  # or: uv pip install bombcell
```

**Problem:** Raw waveforms missing
```python
param["extractRaw"] = True
param["raw_data_file"] = "path/to/recording.bin"
bc.run_bombcell(param)  # Re-run
```

**Problem:** Drift metrics not showing
```python
param["computeDrift"] = True
bc.run_bombcell(param)  # Re-run (adds ~1-2 min)
```

**Problem:** GUI not working
```bash
pip install ipywidgets
jupyter nbextension enable --py widgetsnbextension
```

---

## 📖 Need More Detail?

- **Full documentation:** See `README_NOTEBOOKS.md`
- **BombCell Wiki:** https://github.com/Julie-Fabre/bombcell/wiki
- **Issues:** https://github.com/Julie-Fabre/bombcell/issues

---

## 🎉 You're Ready!

1. Choose your notebook based on your goal
2. Update the `ks_dir` path to your Kilosort output
3. Run cells sequentially
4. Explore and enjoy!

**Happy analyzing! 💣**
