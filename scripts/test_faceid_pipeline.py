import sys
import os
from pathlib import Path
import cv2
import torch
import numpy as np
from PIL import Image

print("Testing FaceID pipeline setup...")
ref_path = "generated/riya_indian_glamour_closeup_lace.png"
if not os.path.exists(ref_path):
    print("Reference image not found:", ref_path)
    sys.exit(1)

# Step 1: Extract Face Embedding
import insightface
from insightface.app import FaceAnalysis
from insightface.utils import face_align

print("Loading InsightFace buffalo_l...")
app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
app.prepare(ctx_id=0, det_size=(640, 640))

img_cv2 = cv2.imread(ref_path)
faces = app.get(img_cv2)
if not faces:
    print("No faces detected!")
    sys.exit(1)

faceid_embeds = torch.from_numpy(faces[0].normed_embedding).unsqueeze(0)
face_image = face_align.norm_crop(img_cv2, landmark=faces[0].kps, image_size=224)
print("Face embedding extracted successfully! Shape:", faceid_embeds.shape)
print("Cropped face image shape:", face_image.shape)
print("Pipeline components verified!")
