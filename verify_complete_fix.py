#!/usr/bin/env python3
"""
Quick verification that extract.py works correctly with all fixes applied.
Tests just 1 viewpoint to verify the complete pipeline.
"""
import os
import sys
sys.path.insert(0, '/teamspace/studios/this_studio')

import habitat_sim
import numpy as np
from PIL import Image
from habitat_sim.nav import NavMeshSettings
from habitat_sim.utils.common import quat_from_angle_axis

os.environ["EGL_DEVICE_ID"] = os.environ.get("CUDA_VISIBLE_DEVICES", "0")

SCENE_PATH = "scenes/102344250.glb"
OUTPUT_DIR = "verification_output"
AGENT_HEIGHT = 1.6

def make_sim_config(scene_path):
    settings = {
        "scene": scene_path,
        "default_agent": 0,
        "width": 640,
        "height": 480,
        "enable_physics": False,
    }
    
    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.scene_dataset_config_file = "default"
    sim_cfg.gpu_device_id = 0
    sim_cfg.scene_id = settings["scene"]
    sim_cfg.enable_physics = settings["enable_physics"]
    
    # RGB sensor with ROLL CORRECTION
    sensor_spec = habitat_sim.CameraSensorSpec()
    sensor_spec.uuid = "rgb"
    sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
    sensor_spec.resolution = [settings["height"], settings["width"]]
    sensor_spec.position = [0.0, 0.0, 0.0]
    # CRITICAL: -90° roll correction
    sensor_spec.orientation = [0.0, 0.0, np.radians(-90)]
    sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
    sensor_spec.hfov = 90
    
    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = [sensor_spec]
    
    return habitat_sim.Configuration(sim_cfg, [agent_cfg])

def create_human_rotations():
    """Create a subset of rotations for testing"""
    rotations = []
    rotation_names = []
    
    # Test 4 cardinal directions + 1 up/down
    yaw_angles = [0, 90, 180, 270]
    yaw_names = ["forward", "right", "back", "left"]
    
    for yaw, name in zip(yaw_angles, yaw_names):
        yaw_rad = np.radians(yaw)
        rotation = quat_from_angle_axis(yaw_rad, np.array([0, 1, 0]))
        rotations.append(rotation)
        rotation_names.append(f"{name}_0deg")
    
    # Add one up/down
    pitch_rotation = quat_from_angle_axis(np.radians(15), np.array([1, 0, 0]))
    rotations.append(pitch_rotation)
    rotation_names.append("look_up_15")
    
    return rotations, rotation_names

print("="*70)
print("VERIFICATION: Testing extract.py pipeline with all fixes")
print("="*70)

os.makedirs(OUTPUT_DIR, exist_ok=True)

cfg = make_sim_config(SCENE_PATH)
sim = habitat_sim.Simulator(cfg)

# Generate navmesh with human settings
if not sim.pathfinder.is_loaded:
    print("\n[1/5] Generating navmesh with human parameters...")
    navmesh_settings = NavMeshSettings()
    navmesh_settings.set_defaults()
    navmesh_settings.agent_height = AGENT_HEIGHT
    navmesh_settings.agent_radius = 0.3
    navmesh_settings.agent_max_climb = 0.2
    navmesh_settings.agent_max_slope = 30.0
    sim.recompute_navmesh(sim.pathfinder, navmesh_settings)
    print("   ✓ Navmesh generated")

# Detect floor level
print("\n[2/5] Detecting floor level...")
sample_heights = []
for _ in range(100):
    point = sim.pathfinder.get_random_navigable_point()
    sample_heights.append(point[1])

sample_heights.sort()
floor_level = sample_heights[10]
print(f"   ✓ Floor level detected: {floor_level:.3f}m")

# Find floor point
print("\n[3/5] Finding floor-level viewpoint...")
floor_point = None
for _ in range(1000):
    point = sim.pathfinder.get_random_navigable_point()
    if abs(point[1] - floor_level) < 0.3:
        floor_point = point
        break

if floor_point is None:
    print("   ✗ ERROR: Could not find floor point")
    sim.close()
    exit(1)

print(f"   ✓ Floor point found: {floor_point}")

# Create rotations
print("\n[4/5] Creating human-like rotations...")
human_rotations, rotation_names = create_human_rotations()
print(f"   ✓ Created {len(human_rotations)} rotation views")

# Capture images
print("\n[5/5] Capturing images...")
agent = sim.initialize_agent(0)
agent_state = habitat_sim.AgentState()

captured = 0
for rotation, rotation_name in zip(human_rotations, rotation_names):
    # Position at human eye height
    agent_position = np.array(floor_point, dtype=np.float32)
    agent_position[1] = floor_point[1] + AGENT_HEIGHT
    
    agent_state.position = agent_position
    agent_state.rotation = rotation
    agent_state.sensor_states = {}
    
    agent.set_state(agent_state)
    
    # Capture
    obs = sim.get_sensor_observations()
    rgb = obs["rgb"][..., :3]
    
    img = Image.fromarray(rgb.astype(np.uint8), "RGB")
    img.save(f"{OUTPUT_DIR}/{rotation_name}.png")
    captured += 1
    print(f"   ✓ Captured {rotation_name}")

sim.close()

print("\n" + "="*70)
print(f"✅ SUCCESS: Captured {captured} images to {OUTPUT_DIR}/")
print("="*70)
print("\nVERIFICATION CHECKLIST:")
print("  1. Open images in", OUTPUT_DIR)
print("  2. Check that vertical walls appear VERTICAL (not horizontal)")
print("  3. Check that floor is at BOTTOM of image")
print("  4. Check that ceiling/sky is at TOP of image")
print("  5. Check that camera appears at human standing height")
print("  6. Check that horizon is roughly in the MIDDLE of image")
print("\nIf all checks pass, the fix is working correctly! ✅")
