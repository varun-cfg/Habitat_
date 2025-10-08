import os
import habitat_sim
import numpy as np
from PIL import Image
from habitat_sim.utils.common import quat_from_angle_axis, quat_to_coeffs
import quaternion

os.environ["EGL_DEVICE_ID"] = os.environ.get("CUDA_VISIBLE_DEVICES", "0")

scene_path = "scenes/102344250.glb"

# Test different sensor configurations
sim_cfg = habitat_sim.SimulatorConfiguration()
sim_cfg.scene_dataset_config_file = "default"
sim_cfg.gpu_device_id = 0
sim_cfg.scene_id = scene_path
sim_cfg.enable_physics = False

# Test Case 1: Default sensor (identity rotation)
sensor_spec = habitat_sim.CameraSensorSpec()
sensor_spec.uuid = "rgb"
sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
sensor_spec.resolution = [480, 640]  # height, width
sensor_spec.position = [0.0, 0.0, 0.0]
sensor_spec.orientation = [0.0, 0.0, 0.0]
sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
sensor_spec.hfov = 90

agent_cfg = habitat_sim.agent.AgentConfiguration()
agent_cfg.sensor_specifications = [sensor_spec]

cfg = habitat_sim.Configuration(sim_cfg, [agent_cfg])
sim = habitat_sim.Simulator(cfg)

# Get a navigable point
if not sim.pathfinder.is_loaded:
    from habitat_sim.nav import NavMeshSettings
    navmesh_settings = NavMeshSettings()
    navmesh_settings.set_defaults()
    sim.recompute_navmesh(sim.pathfinder, navmesh_settings)

floor_point = None
sample_heights = []
for _ in range(100):
    point = sim.pathfinder.get_random_navigable_point()
    sample_heights.append(point[1])

sample_heights.sort()
floor_level = sample_heights[10]

for _ in range(1000):
    point = sim.pathfinder.get_random_navigable_point()
    if abs(point[1] - floor_level) < 0.3:
        floor_point = point
        break

print(f"Floor point: {floor_point}")
print(f"Floor level: {floor_level:.3f}m\n")

agent = sim.initialize_agent(0)
agent_state = habitat_sim.AgentState()

# Set position
agent_position = np.array(floor_point, dtype=np.float32)
agent_position[1] = floor_point[1] + 1.6

output_dir = "debug_rotation"
os.makedirs(output_dir, exist_ok=True)

# Test multiple rotation configurations
test_rotations = [
    ("identity_quat", np.quaternion(1, 0, 0, 0)),
    ("90deg_around_Y", quat_from_angle_axis(np.radians(90), np.array([0, 1, 0]))),
    ("90deg_around_X", quat_from_angle_axis(np.radians(90), np.array([1, 0, 0]))),
    ("90deg_around_Z", quat_from_angle_axis(np.radians(90), np.array([0, 0, 1]))),
    ("-90deg_around_X", quat_from_angle_axis(np.radians(-90), np.array([1, 0, 0]))),
    ("-90deg_around_Z", quat_from_angle_axis(np.radians(-90), np.array([0, 0, 1]))),
    ("combined_fix_attempt_1", quat_from_angle_axis(np.radians(-90), np.array([0, 0, 1])) * quat_from_angle_axis(np.radians(0), np.array([0, 1, 0]))),
    ("combined_fix_attempt_2", quat_from_angle_axis(np.radians(0), np.array([0, 1, 0])) * quat_from_angle_axis(np.radians(90), np.array([0, 0, 1]))),
]

for name, rotation in test_rotations:
    agent_state.position = agent_position
    agent_state.rotation = rotation
    agent.set_state(agent_state)
    
    obs = sim.get_sensor_observations()
    rgb = obs["rgb"][..., :3]
    
    img = Image.fromarray(rgb.astype(np.uint8), "RGB")
    img.save(f"{output_dir}/{name}.png")
    print(f"Saved {name}.png - rotation: {rotation}")

sim.close()
print(f"\n✅ Debug images saved to {output_dir}/")
print("Look for the image where:")
print("  - Vertical walls appear vertical")
print("  - Floor is at bottom, ceiling at top")
print("  - Scene is not rotated 90 degrees")
