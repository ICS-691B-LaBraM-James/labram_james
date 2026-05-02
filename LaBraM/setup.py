import os
import mne
import numpy as np
import h5py
from tqdm import tqdm
import re

DATA_DIR = "data"
OUT_FILE = "labram_ad_control.h5"

# LaBraM standard EEG channels
CHANNELS = [
    'Fp1','Fp2','F7','F3','Fz','F4','F8',
    'T3','C3','Cz','C4','T4','T5','P3','Pz','P4','T6','O1','O2'
]

SFREQ = 200
WINDOW_SEC = 5
WINDOW_SIZE = SFREQ * WINDOW_SEC


def get_label(filename):
    """
    sub-001 to sub-036 => AD (1)
    sub-037 to sub-065 => Control (0)
    """
    match = re.search(r"sub-(\d+)", filename)
    if not match:
        return None

    subj_id = int(match.group(1))

    if 1 <= subj_id <= 36:
        return 1  # AD
    else:
        return 0  # Control


def load_edf(path):
    raw = mne.io.read_raw_edf(path, preload=True, verbose=False)

    # keep only channels that exist
    existing = [ch for ch in CHANNELS if ch in raw.ch_names]
    raw.pick_channels(existing)

    # reorder to match LaBraM expectation
    raw.reorder_channels(existing)

    # preprocess
    raw.resample(SFREQ)
    raw.filter(0.1, 75)

    return raw.get_data()


X, Y = [], []

files = [f for f in os.listdir(DATA_DIR) if f.endswith(".edf")]

print(f"Found {len(files)} files")

for f in tqdm(files):
    path = os.path.join(DATA_DIR, f)

    label = get_label(f)
    if label is None:
        continue

    try:
        data = load_edf(path)

        # windowing
        for i in range(0, data.shape[1] - WINDOW_SIZE, WINDOW_SIZE):
            seg = data[:, i:i+WINDOW_SIZE]

            # sanity check shape
            if seg.shape[0] != len(CHANNELS):
                continue

            X.append(seg)
            Y.append(label)

    except Exception as e:
        print("skip:", f, e)

X = np.array(X, dtype=np.float32)
Y = np.array(Y, dtype=np.int64)

print("FINAL SHAPE:")
print("X:", X.shape)  # (samples, 19, 1000)
print("Y:", Y.shape)

with h5py.File(OUT_FILE, "w") as f:
    f.create_dataset("eeg", data=X)
    f.create_dataset("label", data=Y)

print("Saved to:", OUT_FILE)
