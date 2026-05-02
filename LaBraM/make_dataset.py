import os
import pickle
import mne
import numpy as np
from sklearn.model_selection import train_test_split

DATA_DIR = './data'
OUT_DIR  = './processed'

ALZHEIMERS_END = 36   # sub-001 to sub-036 = AD, sub-037 to sub-065 = CN
WINDOW = 2000         # 10s x 200Hz — matches make_TUAB.py exactly

for split in ['train', 'val', 'test']:
    os.makedirs(os.path.join(OUT_DIR, split), exist_ok=True)

# Collect all files and assign labels
all_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('.edf')])
subjects = []
for fname in all_files:
    sub_id = int(fname.split('_')[0].split('-')[1])
    label  = 1 if sub_id <= ALZHEIMERS_END else 0   # 1=AD, 0=CN
    subjects.append((fname, label))

print(f"Total subjects: {len(subjects)}")
print(f"AD subjects:    {sum(1 for _, l in subjects if l == 1)}")
print(f"CN subjects:    {sum(1 for _, l in subjects if l == 0)}")

# Split at SUBJECT level to avoid data leakage
labels_for_split = [s[1] for s in subjects]
train_subs, temp_subs = train_test_split(
    subjects, test_size=0.3, random_state=42, stratify=labels_for_split
)
temp_labels = [s[1] for s in temp_subs]
val_subs, test_subs = train_test_split(
    temp_subs, test_size=0.5, random_state=42, stratify=temp_labels
)

print(f"\nSubject split:")
print(f"  Train: {len(train_subs)} subjects")
print(f"  Val:   {len(val_subs)} subjects")
print(f"  Test:  {len(test_subs)} subjects")

def process_subject(fname, label, split):
    path = os.path.join(DATA_DIR, fname)
    try:
        raw = mne.io.read_raw_edf(path, preload=True, verbose=False)
        raw.pick_types(eeg=True)

        # Enforce correct channel order — must match exactly
        ch_names = ['FP1', 'FP2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4',
                    'O1',  'O2',  'F7', 'F8', 'T3', 'T4', 'T5', 'T6',
                    'FZ',  'CZ',  'PZ']
        raw.pick_channels(ch_names, ordered=True)

        # Preprocessing to match LaBraM paper
        raw.filter(l_freq=0.1, h_freq=75.0, verbose=False)
        raw.notch_filter(freqs=50, verbose=False)
        raw.resample(200, verbose=False)

        data = raw.get_data(units='uV')   # shape: (19, n_times)

        n_windows = data.shape[1] // WINDOW
        if n_windows == 0:
            print(f"  WARNING {fname}: recording too short, skipping")
            return 0

        for i in range(n_windows):
            segment = data[:, i*WINDOW : (i+1)*WINDOW]  # (19, 2000)
            dump_path = os.path.join(
                OUT_DIR, split,
                f"{os.path.splitext(fname)[0]}_{i}.pkl"
            )
            pickle.dump({"X": segment, "y": label}, open(dump_path, "wb"))

        group = "AD" if label == 1 else "CN"
        print(f"  [{split}] {fname} ({group}): {n_windows} windows saved")
        return n_windows

    except Exception as e:
        print(f"  FAILED {fname}: {e}")
        return 0

print("\nProcessing subjects...")
total_windows = {"train": 0, "val": 0, "test": 0}

for fname, label in train_subs:
    total_windows["train"] += process_subject(fname, label, "train")
for fname, label in val_subs:
    total_windows["val"]   += process_subject(fname, label, "val")
for fname, label in test_subs:
    total_windows["test"]  += process_subject(fname, label, "test")

print(f"\nDone!")
print(f"  Train: {total_windows['train']} windows")
print(f"  Val:   {total_windows['val']} windows")
print(f"  Test:  {total_windows['test']} windows")
print(f"\nOutput in {OUT_DIR}/")
