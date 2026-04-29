import os
import pickle
import numpy as np
import mne
from multiprocessing import Pool

# =========================
# CONFIG
# =========================

DATA_DIR = "./data"
OUT_DIR = "./processed"

os.makedirs(OUT_DIR, exist_ok=True)

# Your label rule:
# 001–036 = AD (1)
# 037–065 = Control (0)

def get_label(filename):
    import re
    sid = int(re.search(r"sub-(\d+)", filename).group(1))
    return 1 if sid <= 36 else 0


# =========================
# CHANNELS (your dataset-safe version)
# =========================

TARGET_CHANNELS = [
    "Fp1","Fp2","F7","F3","Fz","F4","F8",
    "T3","C3","Cz","C4","T4","T5","P3","Pz","P4","T6","O1","O2"
]

SFREQ = 200
WINDOW_SIZE = 2000  # 10 seconds (same as TUAB style)


# =========================
# PROCESS FUNCTION
# =========================

def process_file(file):
    try:
        path = os.path.join(DATA_DIR, file)
        raw = mne.io.read_raw_edf(path, preload=True, verbose=False)

        # --- channel handling (robust version)
        existing = [ch for ch in TARGET_CHANNELS if ch in raw.ch_names]
        raw.pick_channels(existing)
        raw.reorder_channels(existing)

        # --- preprocessing
        raw.filter(0.1, 75)
        raw.resample(SFREQ)

        data = raw.get_data()

        label = get_label(file)

        subject_id = file.split("_")[0]

        out_subdir = os.path.join(OUT_DIR, subject_id)
        os.makedirs(out_subdir, exist_ok=True)

        # --- windowing
        for i in range(0, data.shape[1] - WINDOW_SIZE, WINDOW_SIZE):
            segment = data[:, i:i+WINDOW_SIZE]

            save_path = os.path.join(
                out_subdir,
                f"{file.replace('.edf','')}_{i}.pkl"
            )

            pickle.dump(
                {"X": segment, "y": label},
                open(save_path, "wb"),
            )

        print("processed:", file)

    except Exception as e:
        print("FAILED:", file, e)


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    files = [f for f in os.listdir(DATA_DIR) if f.endswith(".edf")]

    print("Files:", len(files))

    with Pool(8) as p:
        p.map(process_file, files)
