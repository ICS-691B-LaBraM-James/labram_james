import pickle
import os

train_files = os.listdir('./processed/train')
print(f"Train files: {len(train_files)}")

sample = pickle.load(open(f'./processed/train/{train_files[0]}', 'rb'))
print(f"X shape: {sample['X'].shape}")   # should be (19, 2000)
print(f"y label: {sample['y']}")          # should be 0 or 1
