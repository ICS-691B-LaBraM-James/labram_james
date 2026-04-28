"""Lightweight band-power and stability features computed on a raw EDF.

Intended as supplementary signal-processing context for the report LLM, since
LEAD itself only outputs an AD/HC classification and not spectral features.
"""
from __future__ import annotations

import mne
import numpy as np


_BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 45.0),
}


def _dominant_shift_label(rel_powers: dict[str, float]) -> str:
    """Pick the band with highest relative power and label any clinically-relevant shift."""
    dominant = max(rel_powers, key=rel_powers.get)
    if dominant == "alpha":
        return "alpha-dominant (typical)"
    if dominant == "delta":
        return "delta-dominant (significant slowing)"
    if dominant == "theta":
        return "theta-dominant (slowing)"
    if dominant == "beta":
        return "beta-dominant (fast activity)"
    return f"{dominant}-dominant"


def compute_eeg_features(edf_path: str, target_fs: int = 200) -> dict:
    raw = mne.io.read_raw_edf(edf_path, preload=True, verbose="ERROR")
    raw.pick_types(eeg=True)
    raw.filter(0.5, 45.0, verbose="ERROR")
    raw.notch_filter(50, verbose="ERROR")
    raw.resample(target_fs, verbose="ERROR")

    data = raw.get_data() * 1e6  # microvolts
    n_times = data.shape[1]

    freqs = np.fft.rfftfreq(n_times, d=1.0 / target_fs)
    psd = np.abs(np.fft.rfft(data, axis=1)) ** 2

    abs_power: dict[str, float] = {}
    for name, (lo, hi) in _BANDS.items():
        idx = np.where((freqs >= lo) & (freqs < hi))[0]
        # Sum PSD bins within band (= ∫PSD df ≈ total band energy per channel),
        # then average across channels. Standard clinical formulation.
        abs_power[name] = float(psd[:, idx].mean(axis=0).sum()) if len(idx) else 0.0

    total = sum(abs_power.values()) + 1e-8
    rel = {k: v / total for k, v in abs_power.items()}
    theta_alpha = abs_power["theta"] / (abs_power["alpha"] + 1e-8)

    notes: list[str] = []
    if rel["theta"] + rel["delta"] > 0.5:
        notes.append("Increased slow-wave activity (delta/theta dominance)")
    if rel["alpha"] < 0.2:
        notes.append("Reduced alpha activity")
    if theta_alpha > 1.5:
        notes.append("Elevated theta/alpha ratio (generalized slowing pattern)")
    if rel["beta"] < 0.1:
        notes.append("Reduced beta activity")
    if not notes:
        notes.append("EEG spectral pattern within typical physiological range")

    channel_means = data.mean(axis=1)
    stability = float(1.0 - (np.std(channel_means) / (np.mean(np.abs(data)) + 1e-8)))

    return {
        "delta": abs_power["delta"],
        "theta": abs_power["theta"],
        "alpha": abs_power["alpha"],
        "beta": abs_power["beta"],
        "gamma": abs_power["gamma"],
        "relative_powers": rel,
        "dominant_frequency_shift": _dominant_shift_label(rel),
        "theta_alpha_ratio": float(theta_alpha),
        "stability_index": stability,
        "notes": "; ".join(notes),
    }
