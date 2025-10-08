#!/usr/bin/env python3
"""
Comprehensive test to verify human perspective camera setup.
This script tests that:
1. Camera is positioned at correct height above floor
2. Camera is level with horizon (not tilted)
3. Rotations work correctly in all directions
"""

import os
import habitat_sim
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from habitat_sim.nav import NavMeshSettings
from habitat_sim.utils.common import quat_from_angle_axis

os.environ["EGL_DEVICE_ID"] = os.environ.get("CUDA_VISIBLE_DEVICES", "0")

# Configuration
SCENE_PATH = "scenes/102344250.glb"
OUTPUT_DIR = "test_human_perspective"
AGENT_HEIGHT = 1.6  # Human eye height in meters

def make_sim():
    """Create simulator with proper camera configuration"""
    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.scene_dataset_config_file = "default"
    sim_cfg.gpu_device_id = 0
    sim_cfg.scene_id = SCENE_PATH
    sim_cfg.enable_physics = False
    
    # RGB sensor
    sensor_spec = habitat_sim.CameraSensorSpec()
    sensor_spec.uuid = "rgb"
    sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
    sensor_spec.resolution = [480, 640]
    sensor_spec.position = [0.0, 0.0, 0.0]  # At agent position
    # CRITICAL: Apply -90° roll correction for proper camera orientation
    sensor_spec.orientation = [0.0, 0.0, np.radians(-90)]  # [pitch, yaw, roll]
    sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
    sensor_spec.hfov = 90
    
    # Agent config
    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = [sensor_spec]
    
    cfg = habitat_sim.Configuration(sim_cfg, [agent_cfg])
    return habitat_sim.Simulator(cfg)

def find_floor_point(sim):
    """Find a valid floor-level point"""
    if not sim.pathfinder.is_loaded:
        navmesh_settings = NavMeshSettings()
        navmesh_settings.set_defaults()
        navmesh_settings.agent_height = AGENT_HEIGHT
        navmesh_settings.agent_radius = 0.3
        navmesh_settings.agent_max_climb = 0.2
        navmesh_settings.agent_max_slope = 30.0
        sim.recompute_navmesh(sim.pathfinder, navmesh_settings)
    
    # Sample to find floor level
    sample_heights = []
    for _ in range(100):
        point = sim.pathfinder.get_random_navigable_point()
        sample_heights.append(point[1])
    
    sample_heights.sort()
    floor_level = sample_heights[10]  # 10th percentile
    
    print(f"Detected floor level: {floor_level:.3f}m")
    
    # Find a floor-level point
    for _ in range(1000):
        point = sim.pathfinder.get_random_navigable_point()
        if abs(point[1] - floor_level) < 0.3:
            print(f"Found floor point: {point}")
            return point, floor_level
    
    raise RuntimeError("Could not find valid floor point!")

def add_text_to_image(img, text):
    """Add text overlay to image"""
    draw = ImageDraw.Draw(img)
    # Use default font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    # Add background rectangle for text
    bbox = draw.textbbox((10, 10), text, font=font)
    draw.rectangle(bbox, fill=(0, 0, 0, 180))
    draw.text((10, 10), text, fill=(255, 255, 255), font=font)
    return img

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("="*60)
    print("HUMAN PERSPECTIVE CAMERA TEST")
    print("="*60)
    
    sim = make_sim()
    floor_point, floor_level = find_floor_point(sim)
    
    # Test rotations
    test_cases = [
        ("forward", quat_from_angle_axis(np.radians(0), np.array([0, 1, 0]))),
        ("right_90", quat_from_angle_axis(np.radians(90), np.array([0, 1, 0]))),
        ("back_180", quat_from_angle_axis(np.radians(180), np.array([0, 1, 0]))),
        ("left_270", quat_from_angle_axis(np.radians(270), np.array([0, 1, 0]))),
        ("look_up_15", quat_from_angle_axis(np.radians(15), np.array([1, 0, 0]))),
        ("look_down_15", quat_from_angle_axis(np.radians(-15), np.array([1, 0, 0]))),
    ]
    
    agent = sim.initialize_agent(0)
    agent_state = habitat_sim.AgentState()
    
    print(f"\nCapturing test images...")
    print(f"Floor level: {floor_level:.3f}m")
    print(f"Camera height: {floor_level + AGENT_HEIGHT:.3f}m")
    
    for name, rotation in test_cases:
        # Set position at human eye height
        agent_position = np.array(floor_point, dtype=np.float32)
        agent_position[1] = floor_point[1] + AGENT_HEIGHT
        
        agent_state.position = agent_position
        agent_state.rotation = rotation
        agent_state.sensor_states = {}
        
        agent.set_state(agent_state)
        
        # Verify
        actual_state = agent.get_state()
        actual_height = actual_state.position[1]
        expected_height = floor_point[1] + AGENT_HEIGHT
        
        print(f"\n{name}:")
        print(f"  Expected height: {expected_height:.3f}m")
        print(f"  Actual height: {actual_height:.3f}m")
        print(f"  Difference: {abs(actual_height - expected_height):.4f}m")
        
        # Capture image
        obs = sim.get_sensor_observations()
        rgb = obs["rgb"][..., :3]
        
        # Add info overlay
        info_text = f"{name}\nHeight: {actual_height:.2f}m\nFloor+{AGENT_HEIGHT}m"
        img = Image.fromarray(rgb.astype(np.uint8), "RGB")
        img = add_text_to_image(img, info_text)
        
        # Save
        img.save(f"{OUTPUT_DIR}/{name}.png")
        print(f"  ✓ Saved {name}.png")
    
    sim.close()
    
    print(f"\n{'='*60}")
    print(f"✅ Test complete! Images saved to {OUTPUT_DIR}/")
    print(f"{'='*60}")
    print("\nVERIFICATION CHECKLIST:")
    print("  1. Check if images show scene from human standing height")
    print("  2. Horizon should be roughly in middle of forward/right/back/left views")
    print("  3. Look_up should show ceiling/sky")
    print("  4. Look_down should show more floor")
    print("  5. No weird tilting or rotation artifacts")

if __name__ == "__main__":
    main()
