import torch
from modeling_finetune import labram_base_patch200_200 

model = labram_base_patch200_200()
checkpoint = torch.load('./checkpoints/labram-base.pth', map_location='cpu')
if 'model' in checkpoint:
    model.load_state_dict(checkpoint['model'])
else:
    model.load_state_dict(checkpoint)

model.eval()
