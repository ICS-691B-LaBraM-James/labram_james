import mne
import numpy as np

raw = mne.io.read_raw_edf("test.edf", preload=True)

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
