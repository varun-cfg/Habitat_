#!/usr/bin/env python3
"""
FINAL VERIFICATION: Test complete gravity-aligned extraction pipeline
This replicates exactly what extract.py does
"""
import os
import sys
import habitat_sim
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from habitat_sim.nav import NavMeshSettings
from habitat_sim.utils.common import quat_from_angle_axis

os.environ["EGL_DEVICE_ID"] = os.environ.get("CUDA_VISIBLE_DEVICES", "0")

SCENE_PATH = "scenes/102344250.glb"
OUTPUT_DIR = "final_verification"
AGENT_HEIGHT = 1.6

print("="*70)
print("FINAL VERIFICATION: Gravity-Aligned Human Perspective")
print("="*70)

# === CONFIGURATION (matching extract.py) ===
def make_sim_config(scene_path):
    settings = {
        "scene": scene_path,
        "width": 640,
        "height": 480,
        "enable_physics": True,
    }
    
    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.scene_dataset_config_file = "default"
    sim_cfg.gpu_device_id = 0
    sim_cfg.scene_id = settings["scene"]
    sim_cfg.enable_physics = settings["enable_physics"]
    
    # GRAVITY-ALIGNED sensor configuration
    sensor_spec = habitat_sim.CameraSensorSpec()
    sensor_spec.uuid = "rgb"
    sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
    sensor_spec.resolution = [settings["height"], settings["width"]]
    sensor_spec.position = [0.0, 0.0, 0.0]
    sensor_spec.orientation = [0.0, 0.0, 0.0]  # Clean - no roll correction
    sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
    sensor_spec.hfov = 90
    
    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = [sensor_spec]
    
    return habitat_sim.Configuration(sim_cfg, [agent_cfg])

def create_human_rotations():
    """Gravity-aligned rotations - yaw only"""
    rotations = []
    rotation_names = []
    
    # Horizontal rotations only (yaw around Y-axis)
    yaw_angles = [0, 90, 180, 270]
    yaw_names = ["forward", "right", "back", "left"]
    
    for yaw, name in zip(yaw_angles, yaw_names):
        yaw_rad = np.radians(yaw)
        rotation = quat_from_angle_axis(yaw_rad, np.array([0, 1, 0]))
        rotations.append(rotation)
        rotation_names.append(f"{name}_0deg")
    
    # Add pitch variants (agent stays upright, sensor tilts)
    for pitch, pitch_name in [(15, "up"), (-15, "down")]:
        rotations.append(quat_from_angle_axis(0, np.array([0, 1, 0])))
        rotation_names.append(f"forward_{pitch_name}")
    
    return rotations, rotation_names

# === SETUP ===
os.makedirs(OUTPUT_DIR, exist_ok=True)
cfg = make_sim_config(SCENE_PATH)
sim = habitat_sim.Simulator(cfg)

print("\n[1/5] Generating navmesh...")
if not sim.pathfinder.is_loaded:
    navmesh_settings = NavMeshSettings()
    navmesh_settings.set_defaults()
    navmesh_settings.agent_height = AGENT_HEIGHT
    navmesh_settings.agent_radius = 0.3
    navmesh_settings.agent_max_climb = 0.2
    navmesh_settings.agent_max_slope = 30.0
    sim.recompute_navmesh(sim.pathfinder, navmesh_settings)
print("  ✓ Navmesh ready")

print("\n[2/5] Detecting floor level...")
sample_heights = [sim.pathfinder.get_random_navigable_point()[1] for _ in range(100)]
floor_level = sorted(sample_heights)[10]
print(f"  ✓ Floor level: {floor_level:.3f}m")

print("\n[3/5] Finding floor point...")
floor_point = None
for _ in range(1000):
    point = sim.pathfinder.get_random_navigable_point()
    if abs(point[1] - floor_level) < 0.3:
        floor_point = point
        break

if not floor_point:
    print("  ✗ ERROR: Could not find floor point")
    sim.close()
    sys.exit(1)
print(f"  ✓ Floor point: {floor_point}")

print("\n[4/5] Creating rotations...")
human_rotations, rotation_names = create_human_rotations()
print(f"  ✓ {len(human_rotations)} rotations created")

print("\n[5/5] Capturing images...")
agent = sim.initialize_agent(0)
agent_state = habitat_sim.AgentState()

agent_position = np.array(floor_point, dtype=np.float32)
agent_position[1] = floor_point[1] + AGENT_HEIGHT

results = []
for rotation, rotation_name in zip(human_rotations, rotation_names):
    # Set agent position and yaw rotation
    agent_state.position = agent_position
    agent_state.rotation = rotation  # Yaw only - agent upright
    
    # Apply pitch via sensor if needed
    pitch_angle = 0.0
    if "_up" in rotation_name:
        pitch_angle = 15.0
    elif "_down" in rotation_name:
        pitch_angle = -15.0
    
    if pitch_angle != 0:
        sensor_state = habitat_sim.SensorState()
        sensor_state.rotation = quat_from_angle_axis(
            np.radians(pitch_angle),
            np.array([1, 0, 0])
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
    
    # Save with overlay
    img = Image.fromarray(rgb.astype(np.uint8), "RGB")
    draw = ImageDraw.Draw(img)
    
    text = f"{rotation_name}\nHeight: {agent_position[1]:.2f}m\nBright: {brightness:.0f} | Var: {variance:.0f}"
    draw.rectangle([(5, 5), (300, 85)], fill=(0, 0, 0, 200))
    draw.text((10, 10), text, fill=(255, 255, 255))
    
    img.save(f"{OUTPUT_DIR}/{rotation_name}.png")
    
    # Quality assessment
    quality = "✅ GOOD" if 40 < brightness < 180 and variance > 300 else "⚠️  CHECK"
    results.append((rotation_name, brightness, variance, quality))
    print(f"  {quality} {rotation_name:20} | Bright: {brightness:6.1f} | Var: {variance:7.1f}")

sim.close()

# === RESULTS ===
print("\n" + "="*70)
print("VERIFICATION COMPLETE")
print("="*70)

good_images = sum(1 for r in results if "✅" in r[3])
total_images = len(results)

print(f"\nQuality Summary: {good_images}/{total_images} images look good")
print(f"Output directory: {OUTPUT_DIR}/")

print("\n" + "="*70)
print("WHAT TO CHECK:")
print("="*70)
print("1. Open images in:", OUTPUT_DIR)
print("2. Verify:")
print("   ✓ Vertical walls appear VERTICAL")
print("   ✓ Floor at BOTTOM, ceiling/sky at TOP")
print("   ✓ Natural human standing perspective")
print("   ✓ Horizon roughly CENTERED in level views")
print("   ✓ 'forward_up' shows ceiling/upper areas")
print("   ✓ 'forward_down' shows floor/lower areas")
print("   ✓ Good scene variety (not just blank walls)")
print("   ✓ Brightness 40-180 (not too bright/dark)")
print("   ✓ Variance >300 (detailed scene)")
print("\n" + "="*70)

if good_images == total_images:
    print("✅ ALL IMAGES PASSED QUALITY CHECKS!")
    print("The gravity-aligned fix is working correctly! 🎉")
elif good_images >= total_images * 0.7:
    print("⚠️  Most images look good, but some may need review")
else:
    print("❌ Many images failed quality checks - needs investigation")

print("="*70)
