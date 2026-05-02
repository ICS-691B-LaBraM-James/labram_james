import os
import numpy as np
import mne
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from collections import defaultdict
import torch.nn.functional as F

# ======================
# CONFIG
# ======================
DATA_DIR = "/Users/kyesteele/dev/labram_james/LaBraM/data"
SFREQ = 500
WINDOW_SEC = 4
BATCH_SIZE = 32
EPOCHS = 10
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ======================
# LOAD FILES + LABELS
# ======================
samples = []

for i in range(1, 66):
    fname = f"sub-{i:03d}_task-eyesclosed_eeg.edf"
    path = os.path.join(DATA_DIR, fname)

    if not os.path.exists(path):
        continue

    label = 1 if i <= 36 else 0  # AD=1, Control=0
    samples.append((path, label, i))

print(f"Loaded {len(samples)} subjects")

# ======================
# WINDOW EXTRACTION
# ======================
def extract_windows(path, label, sid):
    raw = mne.io.read_raw_edf(path, preload=True, verbose=False)
    raw.pick_types(eeg=True)

    if int(raw.info["sfreq"]) != SFREQ:
        raw.resample(SFREQ)

    data = raw.get_data()

    window_size = int(WINDOW_SEC * SFREQ)
    stride = window_size // 2

    windows = []

    for start in range(0, data.shape[1] - window_size, stride):
        seg = data[:, start:start + window_size]

        # normalize per channel
        seg = (seg - seg.mean(axis=1, keepdims=True)) / (
            seg.std(axis=1, keepdims=True) + 1e-6
        )

        windows.append((seg, label, sid))

    return windows

# build dataset
all_data = []
for path, label, sid in samples:
    all_data.extend(extract_windows(path, label, sid))

print(f"Total windows: {len(all_data)}")

# ======================
# SUBJECT SPLIT
# ======================
subjects = list(set([x[2] for x in all_data]))

train_subj, test_subj = train_test_split(
    subjects, test_size=0.2, random_state=42
)

train_data = [x for x in all_data if x[2] in train_subj]
test_data  = [x for x in all_data if x[2] in test_subj]

# ======================
# DATASET
# ======================
class EEGDataset(Dataset):
    def __init__(self, data):
        self.data = data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        x, y, _ = self.data[idx]
        return torch.tensor(x, dtype=torch.float32), torch.tensor(y)

train_dataset = EEGDataset(train_data)
test_dataset  = EEGDataset(test_data)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)

# ======================
# LOAD LABRAM
# ======================
# ⚠️ CHANGE THIS to your actual import
from labram import LaBraM

model = LaBraM(pretrained=True)

# replace head
model.head = nn.Linear(model.embed_dim, 2)

# freeze encoder
for param in model.parameters():
    param.requires_grad = False

for param in model.head.parameters():
    param.requires_grad = True

model.to(DEVICE)

# ======================
# TRAIN
# ======================
optimizer = optim.Adam(model.head.parameters(), lr=1e-3)
criterion = nn.CrossEntropyLoss()

for epoch in range(EPOCHS):
    model.train()
    total_loss = 0

    for x, y in train_loader:
        x, y = x.to(DEVICE), y.to(DEVICE)

        out = model(x)
        loss = criterion(out, y)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    print(f"Epoch {epoch}: Loss={total_loss:.4f}")

# ======================
# SUBJECT-LEVEL EVAL
# ======================
def evaluate(data, model):
    model.eval()
    subject_probs = defaultdict(list)
    subject_labels = {}

    with torch.no_grad():
        for x, y, sid in data:
            x = torch.tensor(x).unsqueeze(0).to(DEVICE)

            out = model(x)
            prob = F.softmax(out, dim=1)[0, 1].item()

            subject_probs[sid].append(prob)
            subject_labels[sid] = y

    correct = 0
    total = 0

    for sid in subject_probs:
        pred_prob = np.mean(subject_probs[sid])
        pred = 1 if pred_prob > 0.5 else 0
        true = subject_labels[sid]

        if pred == true:
            correct += 1
        total += 1

    acc = correct / total
    print(f"Subject-level accuracy: {acc:.4f}")

evaluate(test_data, model)
