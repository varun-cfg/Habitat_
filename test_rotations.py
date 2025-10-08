#!/usr/bin/env python3
"""
Quick test script to understand Habitat's coordinate system and rotations
"""

import os
import habitat_sim
import numpy as np
from PIL import Image
from habitat_sim.utils.common import quat_from_angle_axis, quat_from_coeffs
import quaternion

# Use GPU 0
os.environ["EGL_DEVICE_ID"] = os.environ.get("CUDA_VISIBLE_DEVICES", "0")

def make_simple_config():
    """Create a minimal simulator configuration"""
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
    
    # RGB sensor
    sensor_spec = habitat_sim.CameraSensorSpec()
    sensor_spec.uuid = "rgb"
    sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
    sensor_spec.resolution = [settings["height"], settings["width"]]
    sensor_spec.position = [0.0, 0.0, 0.0]
    sensor_spec.orientation = [0.0, 0.0, 0.0]
    sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
    sensor_spec.hfov = 90
    
    # Agent config
    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = [sensor_spec]
    
    return habitat_sim.Configuration(sim_cfg, [agent_cfg])

def test_rotation_axis(sim, axis_vector, axis_name, base_position):
    """Test rotation around a specific axis"""
    print(f"\n=== Testing {axis_name}-axis rotation ===")
    
    agent = sim.get_agent(0)
    
    # Test 4 angles: 0°, 90°, 180°, 270°
    angles = [0, 90, 180, 270]
    
    for angle in angles:
        angle_rad = np.radians(angle)
        
        # Create rotation quaternion
        rot_quat = quat_from_angle_axis(angle_rad, np.array(axis_vector))
        
        # Set agent state
        agent_state = habitat_sim.AgentState()
        agent_state.position = base_position
        agent_state.rotation = rot_quat
        agent.set_state(agent_state)
        
        # Get observation
        obs = sim.get_sensor_observations()
        rgb = obs["rgb"]
        
        # Calculate camera direction
        forward_local = np.array([0, 0, -1])
        forward_world = quaternion.rotate_vectors(rot_quat, forward_local)
        
        print(f"  {angle:3d}°: Camera looking at {forward_world}")
        
        # Save image for visual inspection
        img = Image.fromarray(rgb.astype(np.uint8))
        img.save(f"debug_rotation_{axis_name}_{angle:03d}deg.png")

def main():
    """Run rotation tests"""
    print("Testing Habitat coordinate system and rotations...")
    
    # Create simulator
    cfg = make_simple_config()
    sim = habitat_sim.Simulator(cfg)
    
    # Find a good test position
    if sim.pathfinder.is_loaded:
        test_position = sim.pathfinder.get_random_navigable_point()
        test_position[1] += 1.6  # Eye level
    else:
        test_position = np.array([0.0, 1.6, 0.0])
    
    print(f"Test position: {test_position}")
    
    # Test different rotation axes
    axes_to_test = [
        ([1, 0, 0], "X"),     # X-axis (pitch-like)
        ([0, 1, 0], "Y"),     # Y-axis (yaw-like)  
        ([0, 0, 1], "Z"),     # Z-axis (roll-like)
    ]
    
    for axis_vec, axis_name in axes_to_test:
        test_rotation_axis(sim, axis_vec, axis_name, test_position)
    
    sim.close()
    
    print("\n=== Test Complete ===")
    print("Check the generated images to see which axis gives proper wall views:")
    print("- X-axis rotation: Should show pitch up/down movement")
    print("- Y-axis rotation: Should show turning left/right (what we want!)")
    print("- Z-axis rotation: Should show rolling (not what we want)")

if __name__ == "__main__":
    main()