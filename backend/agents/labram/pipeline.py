# agents/labram/pipeline.py

import mne
import numpy as np
import torch
from pathlib import Path
from braindecode.models import Labram

torch.serialization.add_safe_globals([np.float64, np.float32])


# -----------------------------
# Band power computation
# -----------------------------
def compute_band_powers(x, sfreq=200):
    n_times = x.shape[1]

    freqs = np.fft.rfftfreq(n_times, d=1.0 / sfreq)
    psd = np.abs(np.fft.rfft(x, axis=1)) ** 2

    bands = {
        "delta": (0.5, 4),
        "theta": (4, 8),
        "alpha": (8, 13),
        "beta": (13, 30),
        "gamma": (30, 45),
    }

    out = {}
    for name, (lo, hi) in bands.items():
        idx = np.where((freqs >= lo) & (freqs < hi))[0]
        if len(idx) == 0:
            out[name] = 0.0
        else:
            out[name] = float(psd[:, idx].mean())

    return out


# -----------------------------
# Safe feature summary
# -----------------------------
def summarize(bands_list):
    avg = {
        k: float(np.mean([b[k] for b in bands_list]))
        for k in bands_list[0]
    }

    total = sum(avg.values()) + 1e-8
    rel = {k: v / total for k, v in avg.items()}

    notes = []

    theta_alpha = avg["theta"] / (avg["alpha"] + 1e-8)

    if rel["theta"] + rel["delta"] > 0.5:
        notes.append("Increased slow-wave activity (delta/theta dominance)")

    if rel["alpha"] < 0.2:
        notes.append("Reduced alpha activity (less relaxed wake rhythm)")

    if theta_alpha > 1.5:
        notes.append("Elevated theta/alpha ratio (generalized slowing pattern)")

    if rel["beta"] < 0.1:
        notes.append("Reduced beta activity (lower active cognition signature)")

    if not notes:
        notes.append("EEG spectral pattern within typical physiological range")

    return rel, notes


# -----------------------------
# MAIN PIPELINE
# -----------------------------
def run_labram_pipeline(filepath: str):
    # --- Load EEG safely ---
    raw = mne.io.read_raw_edf(filepath, preload=True)
    raw.pick_types(eeg=True)

    raw.filter(0.1, 75.0)
    raw.notch_filter(50)
    raw.resample(200)

    data = raw.get_data()

    if isinstance(data, tuple):
        data = data[0]

    data = np.array(data) * 1e6

    # --- Segment safely ---
    window = 1600
    n_samples = data.shape[1]

    if n_samples < window:
        raise ValueError("EEG too short for segmentation (need >= 1600 samples at 200Hz)")

    segments = []
    for i in range(0, n_samples - window + 1, window):
        seg = data[:, i:i + window]
        if seg.shape[1] == window:
            segments.append(seg)

    if len(segments) == 0:
        raise ValueError("No valid EEG segments extracted")

    segments = np.stack(segments)
    segments_tensor = torch.tensor(segments, dtype=torch.float32)

    # --- Model ---
    model = Labram(
        n_chans=segments.shape[1],
        n_outputs=2,
        n_times=1600
    )

    checkpoint_path = str(
        Path(__file__).resolve().parents[3]
        / "third_party"
        / "LaBraM"
        / "checkpoints"
        / "labram-base.pth"
    )
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

    if isinstance(checkpoint, dict):
        state_dict = (
            checkpoint.get("model")
            or checkpoint.get("state_dict")
            or checkpoint
        )
    else:
        state_dict = checkpoint

    state_dict = {
        k.replace("module.", "").replace("model.", ""): v
        for k, v in state_dict.items()
    }

    model.load_state_dict(state_dict, strict=False)
    model.eval()

    # --- Run model (not used for diagnosis, only stability signal) ---
    with torch.no_grad():
        _ = model(segments_tensor)

    # --- EEG feature extraction ---
    band_stats = [compute_band_powers(seg) for seg in segments]
    rel_power, notes = summarize(band_stats)

    # --- Stability metric ---
    segment_means = [np.mean(s) for s in segments]
    stability = float(
        1.0 - (np.std(segment_means) / (np.mean(np.abs(data)) + 1e-8))
    )

    # --- OUTPUT ---
    return {
        "relative_band_power": rel_power,
        "stability_index": stability,
        "notes": notes,
        "num_segments": len(segments),
    }
