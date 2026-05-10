import mne
import numpy as np
import os

def add_and_save_edf(input_path, output_path, new_channel_name):
    raw = mne.io.read_raw_edf(input_path, preload=True, verbose=False)
    n_samples = raw.n_times
    sfreq = raw.info['sfreq']
    times = np.arange(n_samples) / sfreq
    data = np.sin(2 * np.pi * 10 * times) * 1e-5  # Scale to typical EEG microvolts
    data = data.reshape(1, -1)
    
    info = mne.create_info(ch_names=[new_channel_name], sfreq=sfreq, ch_types=['eeg'])
    new_ch_raw = mne.io.RawArray(data, info)
    
    print(f"Adding channel: {new_channel_name}")
    raw.add_channels([new_ch_raw], force_update_info=True)
    print(f"Saving to: {output_path}")
    # Note: EDF export requires data to be in Volts; MNE handles this if types are set correctly
    raw.export(output_path, fmt='edf', overwrite=True)
    print("Done!")

if __name__ == "__main__":
    input_edf = "/Users/kyesteele/dev/labram_james/data/labram/raw/sub-001_task-eyesclosed_eeg.edf"
    output_edf = "/Users/kyesteele/dev/labram_james/ADDED_CHANNEL.edf"
    
    test_channel = "TEST"
    
    if os.path.exists(input_edf):
        add_and_save_edf(input_edf, output_edf, test_channel)
    else:
        print(f"Error: Could not find {input_edf}")
