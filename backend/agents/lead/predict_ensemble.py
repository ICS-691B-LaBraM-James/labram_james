import argparse
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Sequence, Tuple

# Make the vendored LEAD repo importable.
_LEAD_ROOT = Path(__file__).resolve().parents[2] / "third_party" / "LEAD"
if str(_LEAD_ROOT) not in sys.path:
    sys.path.insert(0, str(_LEAD_ROOT))

import mne
import numpy as np
import torch

from data_provider.uea import normalize_batch_ts
from models import LEADv2

# Training-time channel order used for LEADv2 fine-tuning.
TARGET_CHANNELS: List[str] = [
    "Fp1", "Fp2", "F7", "F3", "Fz", "F4", "F8", "T7", "C3", "Cz", 
    "C4", "T8", "P7", "P3", "Pz", "P4", "P8", "O1", "O2"
]

# Common alias mapping to normalize EDF channel names.
CHANNEL_ALIASES: Dict[str, str] = {
    "T3": "T7", "T4": "T8", "T5": "P7", "T6": "P8", "A1": "M1", "A2": "M2",
}

def _canonical_name(ch_name: str) -> str:
    name = ch_name.strip()
    
    # 1. Strip Prefixes
    for prefix in ("EEG ", "EEG-", "EEG_"):
        if name.upper().startswith(prefix.strip().upper()):
            name = name[len(prefix):]
            break
            
    # 2. Strip Suffixes (Added -AVG here)
    # We convert to upper for the check, but slice the original string
    suffixes = ("-REF", "-LE", "-RE", "_REF", "_LE", "_RE", "-AVG", "_AVG")
    name_upper = name.upper()
    for suffix in suffixes:
        if name_upper.endswith(suffix):
            name = name[: -len(suffix)]
            break
    
    # 3. Clean remaining whitespace
    name = name.replace(" ", "")
    
    # 4. Handle Aliases (T3 -> T7, etc.)
    upper_name = name.upper()
    for alias, replacement in CHANNEL_ALIASES.items():
        if upper_name == alias:
            return replacement
            
    return name

def _build_model_config(seq_len: int, num_class: int = 2) -> SimpleNamespace:
    return SimpleNamespace(
        task_name="finetune", output_attention=False, patch_len=50, stride=50,
        enc_in=19, seq_len=seq_len, d_model=128, n_heads=8, e_layers=12,
        d_ff=256, dropout=0.1, activation="gelu", 
        channel_names=",".join(TARGET_CHANNELS), montage_name="standard_1005",
        augmentations="none", num_class=num_class,
    )

def _load_single_model(model_path: Path, device: torch.device, seq_len: int) -> torch.nn.Module:
    cfg = _build_model_config(seq_len=seq_len, num_class=2)
    model = LEADv2.Model(cfg).to(device)
    ckpt = torch.load(model_path, map_location=device, weights_only=False)
    if isinstance(ckpt, dict) and "state_dict" in ckpt:
        ckpt = ckpt["state_dict"]
    cleaned = {k.replace("module.", ""): v for k, v in ckpt.items() if k != "n_averaged"}
    model.load_state_dict(cleaned, strict=False)
    model.eval()
    return model

def preprocess_edf(edf_path: Path, target_fs: int = 200, low_cut: float = 0.5, 
                   high_cut: float = 45.0, notch: float = 50.0, use_avg_ref: bool = True) -> Tuple[np.ndarray, int]:
    raw = mne.io.read_raw_edf(str(edf_path), preload=True, verbose="ERROR")
    
    # 1. Normalize current names
    raw.rename_channels({ch: _canonical_name(ch) for ch in raw.ch_names})
    
    if notch and notch > 0: raw.notch_filter(freqs=[notch], verbose="ERROR")
    raw.filter(l_freq=low_cut, h_freq=high_cut, verbose="ERROR")
    if use_avg_ref: raw.set_eeg_reference(ref_channels="average", projection=False, verbose="ERROR")

    # 2. Match with TARGET_CHANNELS
    current_ch_upper = {ch.upper(): ch for ch in raw.ch_names}
    found_ordered = [current_ch_upper[t.upper()] for t in TARGET_CHANNELS if t.upper() in current_ch_upper]
    
    # --- FIX STARTS HERE ---
    if not found_ordered:
        raise ValueError(
            f"No matching EEG channels found. \n"
            f"Target: {TARGET_CHANNELS}\n"
            f"Found in File (after cleaning): {raw.ch_names}"
        )

    # Pick only what we found
    raw.pick(found_ordered)
    # --- FIX ENDS HERE ---

    raw.reorder_channels(found_ordered)
    raw.resample(sfreq=target_fs, verbose="ERROR")
    
    data = raw.get_data()
    # Create an empty matrix of zeros for all 19 channels
    full_matrix = np.zeros((len(TARGET_CHANNELS), data.shape[1]), dtype=np.float32)
    
    # Map the data we DID find into the correct rows of the 19-channel matrix
    for i, target in enumerate(TARGET_CHANNELS):
        if target.upper() in current_ch_upper:
            # Find which index in 'data' corresponds to this target
            src_idx = found_ordered.index(current_ch_upper[target.upper()])
            full_matrix[i, :] = data[src_idx, :]
            
    return full_matrix.T, int(target_fs)

def segment_signal(data_tc: np.ndarray, seq_len: int = 400, step: int = 200) -> np.ndarray:
    total_t = data_tc.shape[0]
    starts = list(range(0, total_t - seq_len + 1, step))
    segments = np.stack([data_tc[s : s + seq_len] for s in starts], axis=0)
    return normalize_batch_ts(segments).astype(np.float32)

@torch.no_grad()
def run_inference_on_edf(
    edf_path: str,
    checkpoint_root: str,
    seed_folders: str,
    device: str = "cpu",
    sampling_rate: int = 200,
    seq_len: int = 400,
    batch_size: int = 256,
) -> Dict[str, np.ndarray]:
    """The main entry point called by orchestrator.py"""
    dev = torch.device(device if torch.cuda.is_available() or device == "cpu" else "cpu")
    
    # 1. Load Data
    data_tc, fs = preprocess_edf(Path(edf_path), target_fs=sampling_rate)
    segments_ntc = segment_signal(data_tc, seq_len=seq_len)
    
    # 2. Load Models
    root = Path(checkpoint_root)
    seeds = [s.strip() for s in seed_folders.split(",") if s.strip()]
    models = [_load_single_model(root / s / "checkpoint.pth", dev, seq_len) for s in seeds]
    
    # 3. Inference
    n_segments = segments_ntc.shape[0]
    all_probs = []
    fs_batch = torch.full((batch_size,), float(fs), device=dev, dtype=torch.float32)

    for i in range(0, n_segments, batch_size):
        batch = torch.from_numpy(segments_ntc[i : i + batch_size]).to(dev)
        b_size = batch.shape[0]
        mask = torch.ones((b_size, seq_len), device=dev)
        
        m_probs = []
        for model in models:
            logits = model(batch, mask, None, None, fs_batch[:b_size], None)
            m_probs.append(torch.softmax(logits, dim=1))
        
        all_probs.append(torch.stack(m_probs).mean(0).cpu().numpy())

    probs = np.concatenate(all_probs, axis=0)
    subject_prob = probs.mean(axis=0)
    
    return {
        "subject_prob": subject_prob,
        "subject_label": np.array([subject_prob.argmax()], dtype=np.int64),
        "segment_pred_labels": probs.argmax(axis=1),
        "segment_probs": probs
    }
