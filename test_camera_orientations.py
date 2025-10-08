#!/usr/bin/env python3
"""
Simple test to figure out correct camera orientation in Habitat
"""

import os
import habitat_sim
import numpy as np
from PIL import Image
from habitat_sim.utils.common import quat_from_angle_axis, quat_from_coeffs
import quaternion
import magnum as mn

os.environ["EGL_DEVICE_ID"] = os.environ.get("CUDA_VISIBLE_DEVICES", "0")

def test_camera_orientations():
    """Test different camera orientations to find the correct one"""
    
    # Basic sim config
    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.scene_dataset_config_file = "default"
    sim_cfg.gpu_device_id = 0
    sim_cfg.scene_id = "scenes/102344250.glb"
    sim_cfg.enable_physics = False
    
    # Try different sensor orientations
    test_orientations = [
        (mn.Vector3(0, 0, 0), "default"),
        (mn.Vector3(np.pi/2, 0, 0), "90deg_x"),
        (mn.Vector3(-np.pi/2, 0, 0), "neg90deg_x"),
        (mn.Vector3(0, np.pi/2, 0), "90deg_y"), 
        (mn.Vector3(0, 0, np.pi/2), "90deg_z"),
    ]
    
    for sensor_orientation, name in test_orientations:
        print(f"\n=== Testing sensor orientation: {name} {sensor_orientation} ===")
        
        # RGB sensor with test orientation
        sensor_spec = habitat_sim.CameraSensorSpec()
        sensor_spec.uuid = "rgb"
        sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
        sensor_spec.resolution = [240, 320]
        sensor_spec.position = [0.0, 0.0, 0.0]
        sensor_spec.orientation = sensor_orientation
        sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
        sensor_spec.hfov = 90
        
        # Agent config
        agent_cfg = habitat_sim.agent.AgentConfiguration()
        agent_cfg.sensor_specifications = [sensor_spec]
        
        cfg = habitat_sim.Configuration(sim_cfg, [agent_cfg])
        sim = habitat_sim.Simulator(cfg)
        
        try:
            # Get a test position
            if sim.pathfinder.is_loaded:
                test_pos = sim.pathfinder.get_random_navigable_point()
                test_pos[1] += 1.6
            else:
                test_pos = np.array([0.0, 1.6, 0.0])
            
            # Test with identity agent rotation (no agent rotation)
            agent = sim.get_agent(0)
            agent_state = habitat_sim.AgentState()
            agent_state.position = test_pos
            agent_state.rotation = quat_from_coeffs([1, 0, 0, 0])  # Identity
            agent.set_state(agent_state)
            
            # Get observation
            obs = sim.get_sensor_observations()
            rgb = obs["rgb"]
            
            # Save image
            img = Image.fromarray(rgb.astype(np.uint8))
            img.save(f"camera_test_{name}.png")
            
            print(f"  Saved: camera_test_{name}.png")
            
        except Exception as e:
            print(f"  Error: {e}")
        
        finally:
            sim.close()
    
    print("\n=== Test Complete ===")
    print("Check the generated images to see which sensor orientation gives a proper forward view")

if __name__ == "__main__":
    test_camera_orientations()