#!/usr/bin/env python3
"""
Diagnose orientation issues by testing gravity-aligned agent positioning
"""
import os
import habitat_sim
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from habitat_sim.nav import NavMeshSettings
from habitat_sim.utils.common import quat_from_angle_axis, quat_to_angle_axis
import magnum as mn

os.environ["EGL_DEVICE_ID"] = os.environ.get("CUDA_VISIBLE_DEVICES", "0")

SCENE_PATH = "scenes/102344250.glb"
OUTPUT_DIR = "gravity_aligned_test"
AGENT_HEIGHT = 1.6

def make_sim():
    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.scene_dataset_config_file = "default"
    sim_cfg.gpu_device_id = 0
    sim_cfg.scene_id = SCENE_PATH
    sim_cfg.enable_physics = True  # Enable physics for gravity
    
    # Sensor with NO roll correction first
    sensor_spec = habitat_sim.CameraSensorSpec()
    sensor_spec.uuid = "rgb"
    sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
    sensor_spec.resolution = [480, 640]
    sensor_spec.position = [0.0, 0.0, 0.0]
    sensor_spec.orientation = [0.0, 0.0, 0.0]  # No correction
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

# Find floor point
sample_heights = [sim.pathfinder.get_random_navigable_point()[1] for _ in range(100)]
floor_level = sorted(sample_heights)[10]

floor_point = None
for _ in range(1000):
    point = sim.pathfinder.get_random_navigable_point()
    if abs(point[1] - floor_level) < 0.3:
        floor_point = point
        break

print(f"Floor point: {floor_point}")
print(f"Floor level: {floor_level:.3f}m\n")

agent = sim.initialize_agent(0)
agent_state = habitat_sim.AgentState()

# Test different approaches
test_cases = [
    ("default_identity", np.quaternion(1, 0, 0, 0), "Default identity quaternion"),
    ("yaw_0", quat_from_angle_axis(0, np.array([0, 1, 0])), "0° yaw around Y"),
    ("yaw_90", quat_from_angle_axis(np.radians(90), np.array([0, 1, 0])), "90° yaw around Y"),
]

agent_position = np.array(floor_point, dtype=np.float32)
agent_position[1] = floor_point[1] + AGENT_HEIGHT

for name, rotation, desc in test_cases:
    agent_state.position = agent_position
    agent_state.rotation = rotation
    agent.set_state(agent_state)
    
    actual_state = agent.get_state()
    print(f"\n{name} ({desc}):")
    print(f"  Set rotation: {rotation}")
    print(f"  Got rotation: {actual_state.rotation}")
    print(f"  Position: {actual_state.position}")
    
    # Convert quaternion to axis-angle to understand orientation
    angle, axis = quat_to_angle_axis(actual_state.rotation)
    print(f"  Angle: {np.degrees(angle):.1f}°, Axis: {axis}")
    
    obs = sim.get_sensor_observations()
    rgb = obs["rgb"][..., :3]
    
    # Analyze image
    brightness = rgb.mean()
    variance = rgb.var()
    
    img = Image.fromarray(rgb.astype(np.uint8), "RGB")
    
    # Add overlay
    draw = ImageDraw.Draw(img)
    text = f"{name}\nBrightness: {brightness:.1f}\nVar: {variance:.1f}"
    draw.rectangle([(5, 5), (250, 80)], fill=(0, 0, 0, 180))
    draw.text((10, 10), text, fill=(255, 255, 255))
    
    img.save(f"{OUTPUT_DIR}/{name}.png")
    print(f"  Image: brightness={brightness:.1f}, variance={variance:.1f}")

sim.close()

print(f"\n✅ Test complete! Check {OUTPUT_DIR}/ for diagnostic images")
print("\nLook for images that show:")
print("  - Actual interior scene (not just walls/ceiling)")
print("  - Proper vertical orientation")
print("  - Good variance (>1000) and moderate brightness (<200)")
