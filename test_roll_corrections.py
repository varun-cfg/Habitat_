#!/usr/bin/env python3
"""Test different roll corrections to find the right orientation"""

import os
import habitat_sim
import numpy as np
from PIL import Image

os.environ["EGL_DEVICE_ID"] = os.environ.get("CUDA_VISIBLE_DEVICES", "0")

SCENE_FILE = "scenes/103997919_171031233.glb"
OUTPUT_DIR = "test_roll_corrections"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Test different roll angles
roll_angles = [0, 90, -90, 180]

for roll_deg in roll_angles:
    print(f"\n=== Testing roll={roll_deg}° ===")
    
    # Configure simulator
    backend_cfg = habitat_sim.SimulatorConfiguration()
    backend_cfg.scene_dataset_config_file = "default"
    backend_cfg.scene_id = SCENE_FILE
    backend_cfg.enable_physics = False
    backend_cfg.gpu_device_id = 0
    
    # RGB sensor configuration
    sensor_spec = habitat_sim.CameraSensorSpec()
    sensor_spec.uuid = "rgb"
    sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
    sensor_spec.resolution = [480, 640]
    sensor_spec.position = [0.0, 0.0, 0.0]
    # Test different roll orientations
    roll_rad = np.radians(roll_deg)
    sensor_spec.orientation = [0.0, 0.0, roll_rad]  # [pitch, yaw, roll]
    sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
    sensor_spec.hfov = 90
    
    # Agent configuration
    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = [sensor_spec]
    
    cfg = habitat_sim.Configuration(backend_cfg, [agent_cfg])
    sim = habitat_sim.Simulator(cfg)
    
    # Set agent at a reasonable position
    agent = sim.initialize_agent(0)
    agent_state = habitat_sim.AgentState()
    agent_state.position = np.array([-5.0, -6.8, -1.5], dtype=np.float32)  # Floor + eye height
    # Identity rotation (looking forward along -Z)
    agent_state.rotation = np.quaternion(1, 0, 0, 0)
    agent.set_state(agent_state)
    
    # Capture image
    observations = sim.get_sensor_observations()
    rgb_array = observations["rgb"][:, :, :3]
    
    # Save image
    img = Image.fromarray(rgb_array.astype(np.uint8), "RGB")
    filename = f"roll_{roll_deg:+04d}deg.png"
    filepath = os.path.join(OUTPUT_DIR, filename)
    img.save(filepath)
    print(f"✓ Saved: {filename}")
    print(f"  Mean brightness: {rgb_array.mean():.1f}")
    
    sim.close()

print(f"\n✓ All test images saved to {OUTPUT_DIR}/")
print("Compare the images to see which roll angle produces correct orientation")
