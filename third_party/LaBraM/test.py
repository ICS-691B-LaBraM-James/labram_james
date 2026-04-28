import mne
import numpy as np
import torch
from braindecode.models import Labram

# --- 1. SET UP RECOVERY FOR PYTORCH 2.6+ ---
# Trust the numpy scalar global found in many legacy LaBraM checkpoints
torch.serialization.add_safe_globals([np.core.multiarray.scalar])

# --- 2. PREPROCESSING ---
raw = mne.io.read_raw_edf("/Users/kyesteele/dev/labram_james/LaBraM/data/sub-001_task-eyesclosed_eeg.edf", preload=True)
raw.pick_types(eeg=True)
raw.filter(l_freq=0.1, h_freq=75.0)
raw.notch_filter(freqs=50)
raw.resample(200)

data = raw.get_data() * 1e6
window = 1600
segments_list = []
for i in range(0, data.shape[1] - window, window):
    segments_list.append(data[:, i:i+window])
segments = np.stack(segments_list)
segments_tensor = torch.tensor(segments, dtype=torch.float32)

LABEL_MAP = {0: "No Alzheimer's detected", 1: "Alzheimer's detected"}

# --- 3. MODEL INITIALIZATION & LOADING ---
model = Labram(
    n_chans=segments.shape[1],
    n_outputs=2,
    n_times=1600
)

path_to_weights = "/Users/kyesteele/dev/labram_james/LaBraM/checkpoints/labram-base.pth"

# Load the file (handling potentially nested dicts and M5 CPU/MPS mapping)
checkpoint = torch.load(path_to_weights, map_location='cpu', weights_only=False)

# Extract the actual state dict if it's wrapped in 'model' or 'state_dict' keys
if isinstance(checkpoint, dict):
    if 'model' in checkpoint:
        state_dict = checkpoint['model']
    elif 'state_dict' in checkpoint:
        state_dict = checkpoint['state_dict']
    else:
        state_dict = checkpoint
else:
    state_dict = checkpoint

# Clean prefixes like 'module.' or 'model.' and handle strictness for the output head
new_state_dict = {}
for k, v in state_dict.items():
    name = k.replace('module.', '').replace('model.', '')
    new_state_dict[name] = v

# strict=False allows loading the transformer blocks even if the 'n_outputs' head differs
model.load_state_dict(new_state_dict, strict=False)
model.eval()

# --- 4. ANALYSIS FUNCTIONS ---
def compute_band_powers(segment_np, sfreq=200):
    n_times = segment_np.shape[1]
    freqs = np.fft.rfftfreq(n_times, d=1.0/sfreq)
    fft_vals = np.abs(np.fft.rfft(segment_np, axis=1)) ** 2

    bands = {
        "delta (0.5-4 Hz)":   (0.5, 4),
        "theta (4-8 Hz)":     (4,   8),
        "alpha (8-13 Hz)":    (8,  13),
        "beta (13-30 Hz)":    (13, 30),
        "gamma (30-45 Hz)":   (30, 45),
    }

    band_powers = {}
    for band_name, (flo, fhi) in bands.items():
        idx = np.where((freqs >= flo) & (freqs < fhi))[0]
        band_powers[band_name] = float(fft_vals[:, idx].mean())
    return band_powers

def interpret_band_powers(band_powers):
    delta = band_powers["delta (0.5-4 Hz)"]
    theta = band_powers["theta (4-8 Hz)"]
    alpha = band_powers["alpha (8-13 Hz)"]
    beta  = band_powers["beta (13-30 Hz)"]
    gamma = band_powers["gamma (30-45 Hz)"]

    total = delta + theta + alpha + beta + gamma
    rel = {k: v / (total + 1e-8) for k, v in band_powers.items()}

    slow_wave_dominance = rel["delta (0.5-4 Hz)"] + rel["theta (4-8 Hz)"]
    theta_alpha_ratio = theta / (alpha + 1e-8)

    notes = []
    if slow_wave_dominance > 0.5:
        notes.append("elevated slow-wave (delta/theta) activity, consistent with neurodegeneration")
    if rel["alpha (8-13 Hz)"] < 0.15:
        notes.append("reduced alpha power, reflecting potential posterior cortical dysfunction")
    if theta_alpha_ratio > 1.5:
        notes.append(f"elevated theta/alpha ratio ({theta_alpha_ratio:.2f}), a known AD biomarker")
    if rel["beta (13-30 Hz)"] < 0.1:
        notes.append("reduced beta activity, potentially indicating cholinergic dysfunction")
    if not notes:
        notes.append("band power distribution within expected range for healthy EEG")

    return rel, notes

# --- 5. EXECUTION & INFERENCE ---
all_probs = []
all_band_powers = []

with torch.no_grad():
    output = model(segments_tensor)
    probs = torch.softmax(output, dim=-1)
    all_probs = probs.numpy()

for seg in segments:
    all_band_powers.append(compute_band_powers(seg))

pred_classes = np.argmax(all_probs, axis=-1)
avg_probs = all_probs.mean(axis=0)
dominant_class = int(np.argmax(avg_probs))
confidence = float(avg_probs[dominant_class])

avg_band_powers = {
    band: float(np.mean([bp[band] for bp in all_band_powers]))
    for band in all_band_powers[0]
}
total_p = sum(avg_band_powers.values())
rel_powers = {k: v / (total_p + 1e-8) for k, v in avg_band_powers.items()}
_, eeg_notes = interpret_band_powers(avg_band_powers)

alz_segments = int((pred_classes == 1).sum())
normal_segments = int((pred_classes == 0).sum())
num_segments = len(segments)

# --- 6. FINAL REPORT GENERATION ---
band_lines = "\n".join(f"  - {b}: {rel_powers[b]*100:.1f}%" for b in rel_powers)
notes_lines = "\n".join(f"  - {n}" for n in eeg_notes)

text_output = f"""You are a clinical neurologist reviewing an EEG report for Alzheimer's disease screening.

PATIENT EEG SUMMARY
===================
Recording:
  - EEG channels: {data.shape[0]}
  - Segments analyzed: {num_segments} x {window/200:.1f}s

Model Classification (LaBraM):
  - Overall finding: {LABEL_MAP[dominant_class]} (confidence: {confidence:.1%})
  - Alzheimer's flagging rate: {alz_segments/num_segments*100:.1f}%

EEG Frequency Band Analysis (Relative Power):
{band_lines}

Key EEG Observations:
{notes_lines}

TASK:
1. Interpret patterns vs neurological state.
2. Note findings consistent/inconsistent with AD.
3. Highlight biomarkers of concern.
4. Recommend clinical next steps and note limitations.
"""

print(text_output)

import mne
import numpy as np
import torch
from braindecode.models import Labram


torch.serialization.add_safe_globals([np.core.multiarray.scalar])

LABEL_MAP = {0: "No Alzheimer's detected", 1: "Alzheimer's detected"}


def run_labram_pipeline(filepath: str):
    # --- LOAD EEG ---
    raw = mne.io.read_raw_edf(filepath, preload=True)
    raw.pick_types(eeg=True)
    raw.filter(l_freq=0.1, h_freq=75.0)
    raw.notch_filter(freqs=50)
    raw.resample(200)

    data = raw.get_data() * 1e6

    # --- SEGMENT ---
    window = 1600
    segments_list = []
    for i in range(0, data.shape[1] - window, window):
        segments_list.append(data[:, i:i+window])

    segments = np.stack(segments_list)
    segments_tensor = torch.tensor(segments, dtype=torch.float32)

    # --- MODEL ---
    model = Labram(
        n_chans=segments.shape[1],
        n_outputs=2,
        n_times=1600
    )

    checkpoint_path = "/Users/kyesteele/dev/labram_james/LaBraM/checkpoints/labram-base.pth"
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

    if isinstance(checkpoint, dict):
        state_dict = checkpoint.get("model") or checkpoint.get("state_dict") or checkpoint
    else:
        state_dict = checkpoint

    new_state_dict = {k.replace("module.", "").replace("model.", ""): v for k, v in state_dict.items()}
    model.load_state_dict(new_state_dict, strict=False)
    model.eval()

    # --- INFERENCE ---
    with torch.no_grad():
        output = model(segments_tensor)
        probs = torch.softmax(output, dim=-1).numpy()

    pred_classes = np.argmax(probs, axis=-1)
    avg_probs = probs.mean(axis=0)
    dominant_class = int(np.argmax(avg_probs))
    confidence = float(avg_probs[dominant_class])

    # --- SIMPLE OUTPUT ---
    return {
        "label": LABEL_MAP[dominant_class],
        "confidence": confidence,
        "alzheimer_rate": float((pred_classes == 1).mean()),
        "num_segments": len(segments)
    }
