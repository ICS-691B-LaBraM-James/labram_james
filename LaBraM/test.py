import mne
import numpy as np
import torch
from braindecode.models import Labram

raw = mne.io.read_raw_edf("/Users/kyesteele/dev/labram_james/LaBraM/data/sub-001_task-eyesclosed_eeg.edf", preload=True)
raw.pick_types(eeg=True)
raw.filter(l_freq=0.1, h_freq=75.0)
raw.notch_filter(freqs=50)
raw.resample(200)

data = raw.get_data() * 1e6
window = 1600
segments = []
for i in range(0, data.shape[1] - window, window):
    segments.append(data[:, i:i+window])
segments = np.stack(segments)
segments = torch.tensor(segments, dtype=torch.float32)

LABEL_MAP = {0: "No Alzheimer's detected", 1: "Alzheimer's detected"}

model = Labram(
    n_times=1600,
    n_chans=segments.shape[1],
    n_outputs=2
)
model.eval()

def compute_band_powers(segment_np, sfreq=200):
    """Compute EEG band powers - these are clinically meaningful for Alzheimer's"""
    n_times = segment_np.shape[1]
    freqs = np.fft.rfftfreq(n_times, d=1.0/sfreq)
    fft_vals = np.abs(np.fft.rfft(segment_np, axis=1)) ** 2

    bands = {
        "delta (0.5-4 Hz)":   (0.5, 4),    # increases in Alzheimer's
        "theta (4-8 Hz)":     (4,   8),    # increases in Alzheimer's
        "alpha (8-13 Hz)":    (8,  13),    # decreases in Alzheimer's
        "beta (13-30 Hz)":    (13, 30),    # decreases in Alzheimer's
        "gamma (30-45 Hz)":   (30, 45),    # decreases in Alzheimer's
    }

    band_powers = {}
    for band_name, (flo, fhi) in bands.items():
        idx = np.where((freqs >= flo) & (freqs < fhi))[0]
        band_powers[band_name] = float(fft_vals[:, idx].mean())

    return band_powers

def interpret_band_powers(band_powers):
    """Turn band powers into a clinically meaningful interpretation"""
    delta = band_powers["delta (0.5-4 Hz)"]
    theta = band_powers["theta (4-8 Hz)"]
    alpha = band_powers["alpha (8-13 Hz)"]
    beta  = band_powers["beta (13-30 Hz)"]
    gamma = band_powers["gamma (30-45 Hz)"]

    total = delta + theta + alpha + beta + gamma
    rel   = {k: v / total for k, v in band_powers.items()}

    # Alzheimer's EEG hallmarks: high slow waves, low fast waves
    slow_wave_dominance = rel["delta (0.5-4 Hz)"] + rel["theta (4-8 Hz)"]
    fast_wave_presence  = rel["alpha (8-13 Hz)"]  + rel["beta (13-30 Hz)"]
    theta_alpha_ratio   = theta / (alpha + 1e-8)

    notes = []
    if slow_wave_dominance > 0.5:
        notes.append("elevated slow-wave (delta/theta) activity, consistent with cortical slowing seen in neurodegeneration")
    if rel["alpha (8-13 Hz)"] < 0.15:
        notes.append("reduced alpha power, which may reflect posterior cortical dysfunction associated with Alzheimer's")
    if theta_alpha_ratio > 1.5:
        notes.append(f"elevated theta/alpha ratio ({theta_alpha_ratio:.2f}), a known EEG biomarker for Alzheimer's disease")
    if rel["beta (13-30 Hz)"] < 0.1:
        notes.append("reduced beta activity, potentially indicating cholinergic dysfunction")
    if not notes:
        notes.append("band power distribution within expected range for healthy EEG")

    return rel, notes

# Run model and extract features
all_probs = []
all_band_powers = []

with torch.no_grad():
    output = model(segments)
    probs = torch.softmax(output, dim=-1)
    all_probs = probs.numpy()

for seg in segments.numpy():
    bp = compute_band_powers(seg)
    all_band_powers.append(bp)

# Aggregate
pred_classes = np.argmax(all_probs, axis=-1)
avg_probs = all_probs.mean(axis=0)
dominant_class = int(np.argmax(avg_probs))
confidence = float(avg_probs[dominant_class])

# Average band powers across all segments
avg_band_powers = {
    band: float(np.mean([bp[band] for bp in all_band_powers]))
    for band in all_band_powers[0]
}
total_power = sum(avg_band_powers.values())
rel_powers = {k: v / total_power for k, v in avg_band_powers.items()}
_, eeg_notes = interpret_band_powers(avg_band_powers)

alz_segments = int((pred_classes == 1).sum())
normal_segments = int((pred_classes == 0).sum())
num_segments = len(segments)

band_lines = "\n".join(
    f"  - {band}: {rel_powers[band]*100:.1f}% relative power"
    for band in rel_powers
)
notes_lines = "\n".join(f"  - {n}" for n in eeg_notes)

# Final prompt engineered for MedLLaMA2 reasoning
text_output = f"""You are a clinical neurologist reviewing an EEG report for Alzheimer's disease screening.

PATIENT EEG SUMMARY
===================
Recording:
  - EEG channels: {data.shape[0]}
  - Segments analyzed: {num_segments} x {window/200:.1f}s = {num_segments * window/200:.0f}s total

Model Classification (LaBraM):
  - Overall finding: {LABEL_MAP[dominant_class]} (confidence: {confidence:.1%})
  - Segments flagged as Alzheimer's: {alz_segments} / {num_segments} ({alz_segments/num_segments*100:.1f}%)
  - Segments flagged as normal: {normal_segments} / {num_segments} ({normal_segments/num_segments*100:.1f}%)

EEG Frequency Band Analysis:
{band_lines}

Key EEG Observations:
{notes_lines}

TASK:
Given the above EEG findings, please:
1. Interpret what these patterns suggest about the patient's neurological state
2. Explain which findings are consistent or inconsistent with Alzheimer's disease
3. Highlight any biomarkers of concern
4. Recommend clinical next steps (additional tests, referrals, follow-up)
5. Note any limitations of EEG-based Alzheimer's screening

Provide a detailed clinical reasoning response."""

print(text_output)

# Pass this to MedLLaMA2
medllama2_input = text_output
