#!/usr/bin/env python3
"""
Test gravity-aligned camera with proper sensor orientation
"""
import os
import habitat_sim
import numpy as np
from PIL import Image, ImageDraw
from habitat_sim.nav import NavMeshSettings
from habitat_sim.utils.common import quat_from_angle_axis

os.environ["EGL_DEVICE_ID"] = os.environ.get("CUDA_VISIBLE_DEVICES", "0")

SCENE_PATH = "scenes/102344250.glb"
OUTPUT_DIR = "test_gravity_aligned"
AGENT_HEIGHT = 1.6

def make_sim():
    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.scene_dataset_config_file = "default"
    sim_cfg.gpu_device_id = 0
    sim_cfg.scene_id = SCENE_PATH
    sim_cfg.enable_physics = True
    
    # Sensor configuration - NO roll correction, agent handles orientation
    sensor_spec = habitat_sim.CameraSensorSpec()
    sensor_spec.uuid = "rgb"
    sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
    sensor_spec.resolution = [480, 640]
    sensor_spec.position = [0.0, 0.0, 0.0]  # At agent position
    sensor_spec.orientation = [0.0, 0.0, 0.0]  # Level, agent provides yaw
    sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
    sensor_spec.hfov = 90
    
    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = [sensor_spec]
    
    cfg = habitat_sim.Configuration(sim_cfg, [agent_cfg])
    return habitat_sim.Simulator(cfg)

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("="*70)
print("GRAVITY-ALIGNED CAMERA TEST")
print("="*70)

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

print(f"Floor level: {floor_level:.3f}m")
print(f"Floor point: {floor_point}\n")

agent = sim.initialize_agent(0)
agent_state = habitat_sim.AgentState()

# Test cases: gravity-aligned rotations
test_cases = [
    ("forward_level", quat_from_angle_axis(0, np.array([0, 1, 0])), 0),
    ("right_level", quat_from_angle_axis(np.radians(90), np.array([0, 1, 0])), 0),
    ("back_level", quat_from_angle_axis(np.radians(180), np.array([0, 1, 0])), 0),
    ("left_level", quat_from_angle_axis(np.radians(270), np.array([0, 1, 0])), 0),
    ("forward_up", quat_from_angle_axis(0, np.array([0, 1, 0])), 15),
    ("forward_down", quat_from_angle_axis(0, np.array([0, 1, 0])), -15),
]

agent_position = np.array(floor_point, dtype=np.float32)
agent_position[1] = floor_point[1] + AGENT_HEIGHT

for name, yaw_rotation, pitch_degrees in test_cases:
    agent_state.position = agent_position
    agent_state.rotation = yaw_rotation  # ONLY yaw - agent stays upright
    
    # Apply pitch via sensor if needed
    if pitch_degrees != 0:
        sensor_state = habitat_sim.SensorState()
        sensor_state.rotation = quat_from_angle_axis(
            np.radians(pitch_degrees),
            np.array([1, 0, 0])  # Pitch around X-axis
        )
        agent_state.sensor_states = {"rgb": sensor_state}
    else:
        agent_state.sensor_states = {}
    
    agent.set_state(agent_state)
    
    # Capture
    obs = sim.get_sensor_observations()
    rgb = obs["rgb"][..., :3]
    
    # Analyze
    brightness = rgb.mean()
    variance = rgb.var()
    
    # Save
    img = Image.fromarray(rgb.astype(np.uint8), "RGB")
    draw = ImageDraw.Draw(img)
    text = f"{name}\nBright: {brightness:.0f}\nVar: {variance:.0f}\nPitch: {pitch_degrees}°"
    draw.rectangle([(5, 5), (200, 95)], fill=(0, 0, 0, 180))
    draw.text((10, 10), text, fill=(255, 255, 255))
    
    img.save(f"{OUTPUT_DIR}/{name}.png")
    
    print(f"✓ {name:20} | Brightness: {brightness:6.1f} | Variance: {variance:7.1f}")

sim.close()

print(f"\n{'='*70}")
print(f"✅ Test complete! Images in {OUTPUT_DIR}/")
print(f"{'='*70}")
print("\nLook for:")
print("  • Forward views should show interior, not walls")
print("  • Brightness 50-150 (not 200+)")
print("  • Variance >500 (varied scene, not uniform)")
print("  • Horizon roughly centered in level views")
print("  • Up view shows ceiling, down view shows floor")
