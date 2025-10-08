import os

SCENES_DIR = "/teamspace/studios/this_studio/scenes"
os.makedirs(SCENES_DIR, exist_ok=True)
%cd {SCENES_DIR}
print("Downloading scenes...")
!wget "https://huggingface.co/datasets/hssd/hssd-scenes/resolve/main/scenes/103997919_171031233.glb" -O "103997919_171031233.glb" -q --show-progress
!wget "https://huggingface.co/datasets/hssd/hssd-scenes/resolve/main/scenes/102344250.glb" -O "102344250.glb" -q --show-progress
print("\n✅ Downloads complete.")