import mne
import os
from pathlib import Path

def drop_and_save_edf(input_path, output_path, channels_to_remove):
    raw = mne.io.read_raw_edf(input_path, preload=True, verbose=False)
    existing_channels = [ch for ch in channels_to_remove if ch in raw.ch_names]
    if not existing_channels:
        print("No matching channels found to drop. Saving original as new file.")
    else:
        print(f"Dropping channels: {existing_channels}")
        raw.drop_channels(existing_channels)
    print(f"Saving to: {output_path}")
    raw.export(output_path, fmt='edf', overwrite=True)
    print("Done!")

if __name__ == "__main__":
    input_edf = "/Users/kyesteele/dev/labram_james/data/labram/raw/sub-001_task-eyesclosed_eeg.edf"
    output_edf = "/Users/kyesteele/dev/labram_james/DROPPED_CHANNEL.edf"
    
    to_drop = ["Fp1"]
    
    if os.path.exists(input_edf):
        drop_and_save_edf(input_edf, output_edf, to_drop)
    else:
        print(f"Error: Could not find {input_edf}")
