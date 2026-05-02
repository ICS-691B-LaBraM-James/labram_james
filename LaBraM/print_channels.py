import mne
raw = mne.io.read_raw_edf('./data/sub-001_task-eyesclosed_eeg.edf', preload=False, verbose=False)
print(raw.ch_names)
