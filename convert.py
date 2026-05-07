import mne
import os

os.makedirs('./data', exist_ok=True)

for root, dirs, files in os.walk('../ds004504'):
    if 'derivatives' in dirs:
        dirs.remove('derivatives')
    for filename in files:
        if filename.endswith('.set'):
            path = (os.path.join(root, filename))
            data = mne.io.read_raw_eeglab(path)
            output_path = os.path.join('./data/', f'{os.path.splitext(filename)[0]}.edf')
            if int(filename.split('_')[0].split('-')[1]) > 65:
                continue
            data.export(output_path, fmt='edf', overwrite=True)
