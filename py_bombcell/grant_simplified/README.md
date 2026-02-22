# grant_simplified

A minimal Grant workflow with one run entrypoint and one compact analysis helper.

## Run bombcell

```bash
cd /home/runner/work/bombcell/bombcell/py_bombcell
python grant_simplified/run_bombcell/run_bombcell.py --config grant_simplified/config/recording_config.json --mode batch
python grant_simplified/run_bombcell/run_bombcell.py --config grant_simplified/config/recording_config.json --mode single_probe --target-probe B
```

Run folders are sequential (no date/time tags):

- `<recording_root>/bombcell_01/kilosort4_A/bombcell`
- `<recording_root>/bombcell_02/kilosort4_B/bombcell`

Each probe now exports `cluster_bc_classificationReason.tsv` directly during the run for Phy.

## Files kept intentionally small

- `run_bombcell/grant_config.py`
- `run_bombcell/run_bombcell.py`
- `config/recording_config*.json`
- `analyzing_BC_results/post_analysis_setup.py`
