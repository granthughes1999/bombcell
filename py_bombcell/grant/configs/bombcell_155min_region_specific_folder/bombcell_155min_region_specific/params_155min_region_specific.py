"""
Region- and probe-type–specific Bombcell parameter presets for 155-minute Open Ephys Neuropixels sessions.

Design:
- One BASE preset for 155 min + Open Ephys
- Per-probe overrides keyed by probe letter (A–F)
- Optional mode overrides (e.g., single_probe vs batch)

Usage (example):
    from bombcell_155min_region_specific.params_155min_region_specific import get_params

    params = get_params(probe_id="C", mode="single_probe")
"""

from __future__ import annotations
from copy import deepcopy
from typing import Any, Dict, Optional

Params = Dict[str, Any]

BASE_155MIN_OPENEPHYS: Params = dict(
    # Computation toggles
    extractRaw=True,
    reextractRaw=False,
    nRawSpikesToExtract=2000,
    spikeWidth=61,
    waveformBaselineNoiseWindow=10,

    # Stability handling for long sessions (~155 min)
    computeDrift=True,
    driftBinSize=60,               # seconds
    computeTimeChunks=True,
    deltaTimeChunk=120,            # seconds
    presenceRatioBinSize=120,      # seconds

    # Refractory-period violations
    hillOrLlobetMethod=1,
    tauR_valuesMin=0.0015,
    tauR_valuesMax=0.0020,
    tauR_valuesStep=0.0001,
    tauC=0.0005,

    # Waveform shape / noise gates
    minThreshDetectPeaksTroughs=0.2,
    maxNPeaks=2,
    maxNTroughs=1,
    minWvDuration=150,             # microseconds
    maxWvDuration=850,             # microseconds
    spDecayLinFit=False,
    normalizeSpDecay=True,
    minSpatialDecaySlopeExp=-0.004,
    maxSpatialDecaySlopeExp=-0.0005,
    maxWvBaselineFraction=0.30,
    maxScndPeakToTroughRatio_noise=0.80,

    # Non-somatic gates
    maxPeak1ToPeak2Ratio_nonSomatic=3.0,
    maxMainPeakToTroughRatio_nonSomatic=3.0,
    somatic=True,

    # Multi-unit / quality gates
    minNumSpikes=500,
    maxPercSpikesMissing=0.25,
    maxRPVviolations=0.10,
    minPresenceRatio=0.90,
    maxDrift=80,                   # micrometers
    minAmplitude=40,               # uV
    minSNR=3.5,

    # Optional isolation metrics
    computeDistanceMetrics=True,
    nChannelsIsoDist=8,
    isoDmin=20,
    lratioMax=0.20,
    ssMin=0.10,
)

# --- Per-probe overrides (A–F) ---
PROBE_OVERRIDES_155MIN: Dict[str, Params] = {
    # A: NP2.0 Simplex Lobule & Interposed Nucleus (SIM/IP)
    "A": dict(
        maxNPeaks=4,
        maxNTroughs=3,
        minWvDuration=120,
        maxWvDuration=1400,
        maxWvBaselineFraction=0.40,
        minAmplitude=35,
        minSNR=3.0,
        minPresenceRatio=0.92,
        maxDrift=70,
        nChannelsIsoDist=8,
    ),

    # B: NP1.0 Pontine Gray (PG)
    "B": dict(
        minAmplitude=35,
        minSNR=3.0,
        maxDrift=110,
        minPresenceRatio=0.88,
        maxRPVviolations=0.08,
        deltaTimeChunk=180,
        nChannelsIsoDist=8,
    ),

    # C: NP2.0 Motor Cortex (MoP)
    "C": dict(
        minAmplitude=45,
        minSNR=4.0,
        maxPercSpikesMissing=0.20,
        minPresenceRatio=0.93,
        maxDrift=60,
        maxRPVviolations=0.08,
        nChannelsIsoDist=6,
    ),

    # D: NP2.0 VA/VL thalamus
    "D": dict(
        minNumSpikes=300,
        minAmplitude=40,
        minSNR=3.5,
        minPresenceRatio=0.92,
        maxDrift=70,
        maxRPVviolations=0.10,
        nChannelsIsoDist=4,
    ),

    # E: NP1.0 Substantia Nigra pars reticulata (SNr)
    "E": dict(
        minAmplitude=35,
        minSNR=3.0,
        maxRPVviolations=0.06,
        maxPercSpikesMissing=0.22,
        minPresenceRatio=0.88,
        maxDrift=110,
        nChannelsIsoDist=8,
    ),

    # F: NP1.0 Red Nucleus (RN)
    "F": dict(
        minAmplitude=35,
        minSNR=3.0,
        minPresenceRatio=0.88,
        maxDrift=120,
        maxRPVviolations=0.08,
        nChannelsIsoDist=8,
    ),
}

# --- Mode overrides ---
# Keep this minimal. In practice, most differences between single-probe and batch should be I/O + parallelization,
# not QC thresholds. This allows you to add mode-specific tweaks without duplicating probe presets.
MODE_OVERRIDES: Dict[str, Params] = {
    "single_probe": dict(),
    "batch": dict(),
}

def merge_params(*dicts: Params) -> Params:
    out: Params = {}
    for d in dicts:
        for k, v in d.items():
            out[k] = v
    return out

def get_params(probe_id: str, mode: str = "batch", user_overrides: Optional[Params] = None) -> Params:
    """
    Returns merged parameters for a given probe and mode.

    Precedence:
        BASE_155MIN_OPENEPHYS
        -> MODE_OVERRIDES[mode]
        -> PROBE_OVERRIDES_155MIN[probe_id]
        -> user_overrides
    """
    probe_id = probe_id.upper()
    if probe_id not in PROBE_OVERRIDES_155MIN:
        raise KeyError(f"Unknown probe_id={probe_id!r}. Expected one of: {sorted(PROBE_OVERRIDES_155MIN.keys())}")
    if mode not in MODE_OVERRIDES:
        raise KeyError(f"Unknown mode={mode!r}. Expected one of: {sorted(MODE_OVERRIDES.keys())}")

    merged = merge_params(
        deepcopy(BASE_155MIN_OPENEPHYS),
        MODE_OVERRIDES.get(mode, {}),
        PROBE_OVERRIDES_155MIN.get(probe_id, {}),
        user_overrides or {},
    )
    return merged
