import os
import pickle
import numpy as np

class DS004504:
    def __init__(self, root="./processed", split="train"):
        self.samples = []
        self.labels = []

        split_path = os.path.join(root)

        subjects = sorted(os.listdir(split_path))

        for sub in subjects:
            sub_path = os.path.join(split_path, sub)
            if not os.path.isdir(sub_path):
                continue

            for f in os.listdir(sub_path):
                if not f.endswith(".pkl"):
                    continue

                with open(os.path.join(sub_path, f), "rb") as fp:
                    data = pickle.load(fp)

                self.samples.append(data["X"])
                self.labels.append(data["y"])

        self.samples = np.array(self.samples, dtype=np.float32)
        self.labels = np.array(self.labels, dtype=np.int64)

        print(f"[DS004504] Loaded samples: {len(self.samples)}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx], self.labels[idx]
