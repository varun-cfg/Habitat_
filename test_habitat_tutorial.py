#!/usr/bin/env python3
"""
Test the corrected Habitat rotations based on the official tutorial
"""

import os
import habitat_sim
import numpy as np
from PIL import Image
from habitat_sim.utils.common import quat_from_angle_axis, quat_from_coeffs
import quaternion

os.environ["EGL_DEVICE_ID"] = os.environ.get("CUDA_VISIBLE_DEVICES", "0")

def make_config():
    settings = {
        "scene": "scenes/102344250.glb",
        "width": 320,
        "height": 240,
    }
    
    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.scene_dataset_config_file = "default"
    sim_cfg.gpu_device_id = 0
    sim_cfg.scene_id = settings["scene"]
    sim_cfg.enable_physics = False
    
    sensor_spec = habitat_sim.CameraSensorSpec()
    sensor_spec.uuid = "rgb"
    sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
    sensor_spec.resolution = [settings["height"], settings["width"]]
    sensor_spec.position = [0.0, 0.0, 0.0]
    sensor_spec.orientation = [0.0, 0.0, 0.0]
    sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
    sensor_spec.hfov = 90
    
    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = [sensor_spec]
    
    return habitat_sim.Configuration(sim_cfg, [agent_cfg])

def test_habitat_rotations():
    print("Testing Habitat rotations based on official tutorial...")
    
    cfg = make_config()
    sim = habitat_sim.Simulator(cfg)
    
    # Get test position
    if sim.pathfinder.is_loaded:
        test_pos = sim.pathfinder.get_random_navigable_point()
        test_pos[1] += 1.6
    else:
        test_pos = np.array([0.0, 1.6, 0.0])
    
    agent = sim.get_agent(0)
    
    print(f"Test position: {test_pos}")
    print("\nTesting Y-axis rotations (should turn left/right):")
    
    # Test Y-axis rotations (correct for looking at walls)
    angles = [0, 90, 180, 270]
    names = ["forward", "right", "back", "left"]
    
    for angle, name in zip(angles, names):
        angle_rad = np.radians(angle)
        
        # Y-axis rotation only
        rot_quat = quat_from_angle_axis(angle_rad, np.array([0, 1, 0]))
        
        # Set agent state
        agent_state = habitat_sim.AgentState()
        agent_state.position = test_pos
        agent_state.rotation = rot_quat
        agent.set_state(agent_state)
        
        # Calculate camera direction
        forward_local = np.array([0, 0, -1])  # Habitat default
        forward_world = quaternion.rotate_vectors(rot_quat, forward_local)
        
        print(f"  {angle:3d}° ({name:7s}): Looking at {forward_world}")
        
        # Save test image
        obs = sim.get_sensor_observations()
        img = Image.fromarray(obs["rgb"].astype(np.uint8))
        img.save(f"habitat_test_{name}_{angle:03d}deg.png")
    
    sim.close()
    print("\nCheck the generated images to verify wall coverage!")

if __name__ == "__main__":
    test_habitat_rotations()