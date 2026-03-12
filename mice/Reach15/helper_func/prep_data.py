import sys
from pathlib import Path

# new code
from pathlib import Path
from helper_func.nwb_data_prep import build_session_grant_config  # adjust if name differs

def set_bc_paths(session_data_dic, MOUSE,NWB_FILE, NP_FILE, BOMBCELL, BEHAVIORAL_FOLDER, DATE, SESSION, SESSION_TO_ANALYZE):
    # SET #1: Path to the NWB file for this session (on the neural data computer)
    NWB_PATH = Path(fr"H:\Grant\Neuropixel_Analysis\NWB\{NWB_FILE}")

    # SET #2: Path to the bombcell root folder for this session (on the neural data computer)
    BOMBCELL_ROOT_FOR_AUTO_BUILD = Path(fr"H:\Grant\Neuropixel_Analysis\BOMBCELL\{NP_FILE}\{BOMBCELL}")

    # SET #3: Session name for labeling plots
    SESSION_NAME = NP_FILE

    # SET #4: Paths to trial index files (behavior acquisition computer)
    baseline_trials_index_path = rf"G:\Grant\behavior_data\DLC_net\{BEHAVIORAL_FOLDER}\videos\{DATE}\christielab\{SESSION}\{DATE}_christielab_{SESSION}_baseline_trial_numbers_tone2_aligned.npy"
    washout_trials_index_path = rf"G:\Grant\behavior_data\DLC_net\{BEHAVIORAL_FOLDER}\videos\{DATE}\christielab\{SESSION}\{DATE}_christielab_{SESSION}_washout_trial_numbers_tone2_aligned.npy"
    optoicalStim_trials_index_path = rf"G:\Grant\behavior_data\DLC_net\{BEHAVIORAL_FOLDER}\videos\{DATE}\christielab\{SESSION}\{DATE}_christielab_{SESSION}_stim_allowed_trial_numbers_tone2_aligned.npy"
    print(f"Baseline trials index path: {baseline_trials_index_path}")
    print(f"Washout trials index path: {washout_trials_index_path}")
    print(f"Optical stim trials index path: {optoicalStim_trials_index_path}")
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


def extract_start_times(df_stim):

    frame_events_df = df_stim[df_stim['stimulus'] == 'frame_events_timestamp']
    tone1_df = df_stim[df_stim['stimulus'] == 'tone1_timestamps']
    tone2_df = df_stim[df_stim['stimulus'] == 'tone2_timestamps']
    optical_df = df_stim[df_stim['stimulus'] == 'optical_timestamps']
    stim_ROI_df = df_stim[df_stim['stimulus'] == 'stimROI_timestamps']
    all_stimROI_triggers = df_stim[df_stim['stimulus'] == 'reachInit_stimROI_timestamps']

    tone1_start_times = tone1_df['start_time'].values
    tone2_start_times = tone2_df['start_time'].values
    frame_events_start_times = frame_events_df['start_time'].values
    stimROI_start_times = stim_ROI_df['start_time'].values
    optical_start_times = optical_df['start_time'].values
    all_stimROI_triggers_start_times = all_stimROI_triggers['start_time'].values

    print(f"Total Tone1 start_times: {len(tone1_start_times)}")
    print(f"Total Tone2 start_times: {len(tone2_start_times)}")
    print(f"Total Frame Events start_times: {len(frame_events_start_times)}")
    print(f"Total stimROI start_times: {len(stimROI_start_times)}")
    print(f"Total Optical start_times: {len(optical_start_times)}")
    print(f"Total reachInit_stimROI start_times: {len(all_stimROI_triggers_start_times)}")

    return (
        tone1_start_times,
        tone2_start_times,
        frame_events_start_times,
        stimROI_start_times,
        optical_start_times,
        all_stimROI_triggers_start_times,
    )

