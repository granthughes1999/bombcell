from __future__ import annotations

from pathlib import Path
import sys
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from grant_config import load_grant_config, notebook_runtime_context  # noqa: E402


def load_post_analysis_context(config_path: str | Path = "../configs/grant_recording_config.json") -> Dict[str, Any]:
    cfg = load_grant_config(config_path)
    ctx = notebook_runtime_context(cfg)
    for p in [
        ctx["DEFAULT_KS_STAGING_ROOT"],
        ctx["NP20_KS_STAGING_ROOT"],
        ctx["BOMBCELL_KS_SINGLEPROBE_STAGING_ROOT"],
        ctx["DEFAULT_EXPORT_ROOT"],
        ctx["NP20_EXPORT_ROOT"],
        ctx["SINGLE_EXPORT_ROOT"],
    ]:
        p.mkdir(parents=True, exist_ok=True)
    return ctx
