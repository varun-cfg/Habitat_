#!/usr/bin/env python3
"""Quick test with the roll correction applied"""
import os
import habitat_sim
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from habitat_sim.nav import NavMeshSettings
from habitat_sim.utils.common import quat_from_angle_axis

os.environ["EGL_DEVICE_ID"] = os.environ.get("CUDA_VISIBLE_DEVICES", "0")

SCENE_PATH = "scenes/102344250.glb"
OUTPUT_DIR = "test_roll_fix"
AGENT_HEIGHT = 1.6

def make_sim():
    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.scene_dataset_config_file = "default"
    sim_cfg.gpu_device_id = 0
    sim_cfg.scene_id = SCENE_PATH
    sim_cfg.enable_physics = False
    
    # RGB sensor WITH ROLL CORRECTION
    sensor_spec = habitat_sim.CameraSensorSpec()
    sensor_spec.uuid = "rgb"
    sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
    sensor_spec.resolution = [480, 640]
    sensor_spec.position = [0.0, 0.0, 0.0]
    # Apply -90 degree roll correction
    sensor_spec.orientation = [0.0, 0.0, np.radians(-90)]
    sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
    sensor_spec.hfov = 90
    
    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = [sensor_spec]
    
    cfg = habitat_sim.Configuration(sim_cfg, [agent_cfg])
    return habitat_sim.Simulator(cfg)

os.makedirs(OUTPUT_DIR, exist_ok=True)
sim = make_sim()

# Setup navmesh
if not sim.pathfinder.is_loaded:
    navmesh_settings = NavMeshSettings()
    navmesh_settings.set_defaults()
    navmesh_settings.agent_height = AGENT_HEIGHT
    navmesh_settings.agent_radius = 0.3
    navmesh_settings.agent_max_climb = 0.2
    navmesh_settings.agent_max_slope = 30.0
    sim.recompute_navmesh(sim.pathfinder, navmesh_settings)

# Find floor level
sample_heights = []
for _ in range(100):
    point = sim.pathfinder.get_random_navigable_point()
    sample_heights.append(point[1])

sample_heights.sort()
floor_level = sample_heights[10]

# Find floor point
floor_point = None
for _ in range(1000):
    point = sim.pathfinder.get_random_navigable_point()
    if abs(point[1] - floor_level) < 0.3:
        floor_point = point
        break

print(f"Floor level: {floor_level:.3f}m")
print(f"Floor point: {floor_point}\n")

agent = sim.initialize_agent(0)
agent_state = habitat_sim.AgentState()

# Test rotations with roll correction applied
test_cases = [
    ("forward", quat_from_angle_axis(np.radians(0), np.array([0, 1, 0]))),
    ("right_90", quat_from_angle_axis(np.radians(90), np.array([0, 1, 0]))),
    ("back_180", quat_from_angle_axis(np.radians(180), np.array([0, 1, 0]))),
    ("left_270", quat_from_angle_axis(np.radians(270), np.array([0, 1, 0]))),
    ("look_up", quat_from_angle_axis(np.radians(15), np.array([1, 0, 0]))),
    ("look_down", quat_from_angle_axis(np.radians(-15), np.array([1, 0, 0]))),
]

for name, rotation in test_cases:
    agent_position = np.array(floor_point, dtype=np.float32)
    agent_position[1] = floor_point[1] + AGENT_HEIGHT
    
    agent_state.position = agent_position
    agent_state.rotation = rotation
    agent_state.sensor_states = {}
    
    agent.set_state(agent_state)
    
    obs = sim.get_sensor_observations()
    rgb = obs["rgb"][..., :3]
    
    img = Image.fromarray(rgb.astype(np.uint8), "RGB")
    img.save(f"{OUTPUT_DIR}/{name}.png")
    print(f"✓ Saved {name}.png")

sim.close()
print(f"\n✅ Test complete! Check {OUTPUT_DIR}/ for images")
print("Verify:")
print("  - Vertical walls should now appear vertical")
print("  - Floor at bottom, ceiling at top")
print("  - No 90-degree rotation")
