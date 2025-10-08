import os
import habitat_sim
import numpy as np
from PIL import Image
from habitat_sim.utils.common import quat_from_angle_axis, quat_to_coeffs

os.environ["EGL_DEVICE_ID"] = os.environ.get("CUDA_VISIBLE_DEVICES", "0")

# Test the orientation system
scene_path = "scenes/102344250.glb"

# Create simulator config
sim_cfg = habitat_sim.SimulatorConfiguration()
sim_cfg.scene_dataset_config_file = "default"
sim_cfg.gpu_device_id = 0
sim_cfg.scene_id = scene_path
sim_cfg.enable_physics = False

# RGB sensor configuration
sensor_spec = habitat_sim.CameraSensorSpec()
sensor_spec.uuid = "rgb"
sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
sensor_spec.resolution = [480, 640]
sensor_spec.position = [0.0, 0.0, 0.0]  # At agent position
sensor_spec.orientation = [0.0, 0.0, 0.0]  # No additional rotation
sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE

# Agent configuration
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

# Sample floor heights
print("Sampling floor heights...")
sample_heights = []
for _ in range(100):
    point = sim.pathfinder.get_random_navigable_point()
    sample_heights.append(point[1])

sample_heights.sort()
floor_level = sample_heights[10]
print(f"Floor level: {floor_level:.3f}m")

# Find a floor-level point
floor_point = None
for _ in range(1000):
    point = sim.pathfinder.get_random_navigable_point()
    if abs(point[1] - floor_level) < 0.3:
        floor_point = point
        break

if floor_point is None:
    print("Could not find floor point!")
    sim.close()
    exit(1)

print(f"\nFloor point: {floor_point}")

# Test different rotations
agent = sim.initialize_agent(0)
agent_state = habitat_sim.AgentState()

test_cases = [
    ("identity", np.quaternion(1, 0, 0, 0)),
    ("forward_0deg", quat_from_angle_axis(0, np.array([0, 1, 0]))),
    ("forward_habitat_default", quat_from_angle_axis(np.radians(0), np.array([0, 1, 0]))),
    ("pitch_up_15", quat_from_angle_axis(np.radians(15), np.array([1, 0, 0]))),
    ("pitch_down_15", quat_from_angle_axis(np.radians(-15), np.array([1, 0, 0]))),
]

output_dir = "test_orientation_output"
os.makedirs(output_dir, exist_ok=True)

for name, rotation in test_cases:
    # Set position at human eye height
    agent_position = np.array(floor_point, dtype=np.float32)
    agent_position[1] = floor_point[1] + 1.6  # Human eye height
    
    agent_state.position = agent_position
    agent_state.rotation = rotation
    agent.set_state(agent_state)
    
    # Get observation
    obs = sim.get_sensor_observations()
    rgb = obs["rgb"][..., :3]
    
    # Save image
    img = Image.fromarray(rgb.astype(np.uint8), "RGB")
    img.save(f"{output_dir}/{name}.png")
    
    print(f"Saved {name}.png")
    print(f"  Position: {agent.get_state().position}")
    print(f"  Rotation: {agent.get_state().rotation}")

sim.close()
print(f"\n✅ Test images saved to {output_dir}/")
print("Please check if any of these show correct human-level perspective.")
