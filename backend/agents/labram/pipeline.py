# agents/labram/pipeline.py
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
