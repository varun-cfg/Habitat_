#!/usr/bin/env python3
"""Test different sensor orientations to find the correct human perspective"""

import os
import habitat_sim
import numpy as np
from PIL import Image

os.environ["EGL_DEVICE_ID"] = os.environ.get("CUDA_VISIBLE_DEVICES", "0")

def test_orientation(roll_degrees, output_filename):
    """Test a specific roll angle and save the result"""
    
    # Scene setup
    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.scene_dataset_config_file = "default"
    sim_cfg.scene_id = "scenes/103997919_171031233.glb"
    sim_cfg.enable_physics = False
    sim_cfg.gpu_device_id = 0
    
    # Sensor setup
    sensor_spec = habitat_sim.CameraSensorSpec()
    sensor_spec.uuid = "rgb"
    sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
    sensor_spec.resolution = [480, 640]  # [height, width]
    sensor_spec.position = [0.0, 0.0, 0.0]
    
    # Test different orientations
    roll_rad = np.radians(roll_degrees)
    sensor_spec.orientation = [0.0, 0.0, roll_rad]  # [pitch, yaw, roll]
    sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
    sensor_spec.hfov = 90
    
    # Agent setup
    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = [sensor_spec]
    
    cfg = habitat_sim.Configuration(sim_cfg, [agent_cfg])
    sim = habitat_sim.Simulator(cfg)
    
    # Position agent at a good viewpoint (from previous successful run)
    agent = sim.initialize_agent(0)
    agent_state = habitat_sim.AgentState()
    agent_state.position = np.array([-7.09, -6.78, -1.18], dtype=np.float32)  # Floor + 1.6m height
    agent_state.rotation = np.quaternion(1, 0, 0, 0)  # Looking forward
    agent.set_state(agent_state)
    
    # Capture image
    observations = sim.get_sensor_observations()
    rgb_array = observations["rgb"][:, :, :3]
    
    # Save image
    img = Image.fromarray(rgb_array.astype(np.uint8), "RGB")
    img.save(f"orientation_test/{output_filename}")
    
    sim.close()
    return rgb_array.mean()

# Create test directory
os.makedirs("orientation_test", exist_ok=True)

# Test different roll angles to find the correct human perspective
test_angles = [0, 45, 90, 135, 180, 225, 270, 315, -90, -45]

print("=== Testing Different Sensor Orientations ===")
print("Looking for the orientation where:")
print("- Floor is horizontal at the bottom")
print("- Ceiling is horizontal at the top") 
print("- Walls are vertical")
print("- Objects appear upright")

for angle in test_angles:
    filename = f"roll_{angle:+04d}deg.png"
    try:
        brightness = test_orientation(angle, filename)
        print(f"Roll {angle:+4d}°: {filename} (brightness: {brightness:.1f})")
    except Exception as e:
        print(f"Roll {angle:+4d}°: FAILED - {e}")

print(f"\n✓ Test images saved to orientation_test/")
print("Check each image to find which roll angle gives proper human perspective:")
print("- roll_+000deg.png = No roll correction")
print("- roll_+090deg.png = +90° roll (current setting)")
print("- roll_-090deg.png = -90° roll") 
print("- etc.")