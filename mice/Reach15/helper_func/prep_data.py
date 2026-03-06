import sys
from pathlib import Path

# new code
from pathlib import Path
from helper_func.nwb_data_prep import build_session_grant_config  # adjust if name differs

def set_bc_paths(session_data_dic, MOUSE,NWB_FILE, NP_FILE, BOMBCELL, BEHAVIORAL_FOLDER, DATE, SESSION, SESSION_TO_ANALYZE):
    # SET #1: Path to the NWB file for this session (on the neural data computer)
    NWB_PATH = Path(fr"H:\NWB_OUT\{NWB_FILE}")

    # SET #2: Path to the bombcell root folder for this session (on the neural data computer)
    BOMBCELL_ROOT_FOR_AUTO_BUILD = Path(fr"H:\Grant\Neuropixels\Kilosort_Recordings\{NP_FILE}\bombcell\{BOMBCELL}")

    # SET #3: Session name for labeling plots
    SESSION_NAME = NP_FILE

    # SET #4: Paths to trial index files (behavior acquisition computer)
    baseline_trials_index_path = rf"G:\Grant\behavior_data\DLC_net\{BEHAVIORAL_FOLDER}\videos\{DATE}\christielab\{SESSION}\{DATE}_christielab_{SESSION}_baseline_trial_numbers_tone2_aligned.npy"
    washout_trials_index_path = rf"G:\Grant\behavior_data\DLC_net\{BEHAVIORAL_FOLDER}\videos\{DATE}\christielab\{SESSION}\{DATE}_christielab_{SESSION}_washout_trial_numbers_tone2_aligned.npy"
    optoicalStim_trials_index_path = rf"G:\Grant\behavior_data\DLC_net\{BEHAVIORAL_FOLDER}\videos\{DATE}\christielab\{SESSION}\{DATE}_christielab_{SESSION}_stim_allowed_trial_numbers_tone2_aligned.npy"

    # SET #5: Auto-generate a session-specific config file from .env + selected session
    CONFIG_FILE, _ = build_session_grant_config(
        session_data_dic=session_data_dic,
        session_selection=SESSION_TO_ANALYZE,
        verbose=True,
    )

    for required_path, label in [
        (baseline_trials_index_path, "baseline trials index"),
        (washout_trials_index_path, "washout trials index"),
        (optoicalStim_trials_index_path, "optical stim trials index"),
        # (NWB_PATH, "NWB file"),
        # (BOMBCELL_ROOT_FOR_AUTO_BUILD, "Bombcell root folder"),
        (CONFIG_FILE, "session config file"),
    ]:
        if not Path(required_path).exists():
            raise FileNotFoundError(f"Missing {label}: {required_path}")

    print("All required files/folders found.")
    print(f"NWB file: {NWB_PATH}")
    print(f"Bombcell root folder: {BOMBCELL_ROOT_FOR_AUTO_BUILD}")
    print(f"Session config file: {CONFIG_FILE}")

    return BOMBCELL_ROOT_FOR_AUTO_BUILD, NWB_PATH, CONFIG_FILE, SESSION_NAME

