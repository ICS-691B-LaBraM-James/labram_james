# STUB — Replace with real MNE-Python pipeline
# Real pipeline steps:
#   1. mne.io.read_raw_* to load bytes as Raw object
#   2. Bandpass filter 0.5–50 Hz
#   3. Notch filter at 60 Hz
#   4. Detect and interpolate bad channels
#   5. ICA for eye blink and muscle artifact removal
#   6. AutoReject for epoch-level rejection
#   7. Epoch into fixed-length windows
#   8. Return cleaned epochs as numpy array


def clean_eeg(raw_bytes: bytes) -> dict:
    print("[EEG Cleaner] Cleaning EEG data... (stub)")
    return {
        "status": "cleaned",
        "n_channels": 64,
        "sampling_rate": 256,
        "duration_seconds": 30,
        "artifacts_removed": 3,
        "epochs": [],
    }
