import os
import habitat_sim
import numpy as np
from PIL import Image
from habitat_sim.nav import NavMeshSettings
from habitat_sim.utils.common import quat_from_angle_axis, quat_from_coeffs, quat_to_coeffs
import quaternion

# This line explicitly tells the EGL system which GPU to use.
os.environ["EGL_DEVICE_ID"] = os.environ.get("CUDA_VISIBLE_DEVICES", "0")

# --- Configuration ---
SCENE_FILES = [
    "scenes/103997919_171031233.glb",
    "scenes/102344250.glb"
]
BASE_OUTPUT_DIR = "extraction_output_human_perspective"
NUM_VIEWPOINTS_PER_SCENE = 10
AGENT_HEIGHT = 1.6  # Standard human eye height in meters (avg adult: 1.5-1.7m)
MIN_BRIGHTNESS_THRESHOLD = 15
MIN_VARIANCE_THRESHOLD = 150
ENABLE_PHYSICS = True  # Set to True if agent positioning issues persist

def is_valid_image(rgb_array):
    """Check if the image is valid (not black, not uniform, has sufficient detail)"""
    if rgb_array is None or rgb_array.size == 0:
        return False
    
    # Convert to grayscale for brightness check
    gray = np.dot(rgb_array[...,:3], [0.2989, 0.5870, 0.1140])
    
    # Check average brightness
    avg_brightness = np.mean(gray)
    if avg_brightness < MIN_BRIGHTNESS_THRESHOLD:
        return False
    
    # Check variance (to avoid uniform color images)
    variance = np.var(gray)
    if variance < MIN_VARIANCE_THRESHOLD:
        return False
    
    # Check if too much of the image is black
    black_pixels = np.sum(np.all(rgb_array < 25, axis=2))
    total_pixels = rgb_array.shape[0] * rgb_array.shape[1]
    black_ratio = black_pixels / total_pixels
    
    if black_ratio > 0.6:  # More than 60% black pixels
        return False
    
    # Check for reasonable color distribution
    mean_color = np.mean(rgb_array.reshape(-1, 3), axis=0)
    if np.all(mean_color < 20):  # Very dark image
        return False
    
    return True

def make_sim_config(scene_path):
    settings = {
        "scene": scene_path,
        "default_agent": 0,
        "width": 640,
        "height": 480,
        "enable_physics": ENABLE_PHYSICS,
    }
    
    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.scene_dataset_config_file = "default"
    sim_cfg.gpu_device_id = 0
    sim_cfg.scene_id = settings["scene"]
    sim_cfg.enable_physics = settings["enable_physics"]
    
    # RGB sensor configuration
    sensor_spec = habitat_sim.CameraSensorSpec()
    sensor_spec.uuid = "rgb"
    sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
    sensor_spec.resolution = [settings["height"], settings["width"]]
    # Sensor at agent's eye position (no offset)
    sensor_spec.position = [0.0, 0.0, 0.0]
    
    # CRITICAL FIX: The sensor default orientation in Habitat can be inconsistent
    # We need to ensure it looks forward horizontally
    # Some Habitat versions have the camera looking down by default
    # A 90-degree rotation around X-axis tilts from looking down to looking forward
    sensor_spec.orientation = [0.0, 0.0, 0.0]  # We'll handle rotation at agent level
    
    sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
    sensor_spec.hfov = 90  # 90° horizontal FOV (natural human vision)
    
    # Agent configuration
    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = [sensor_spec]
    agent_cfg.action_space = {
        "move_forward": habitat_sim.agent.ActionSpec("move_forward", habitat_sim.agent.ActuationSpec(amount=0.25)),
        "turn_left": habitat_sim.agent.ActionSpec("turn_left", habitat_sim.agent.ActuationSpec(amount=30.0)),
        "turn_right": habitat_sim.agent.ActionSpec("turn_right", habitat_sim.agent.ActuationSpec(amount=30.0)),
    }
    
    return habitat_sim.Configuration(sim_cfg, [agent_cfg])

def correct_camera_orientation_quaternion():
    """Create a base quaternion to correct camera orientation.
    
    If the camera is looking down (bird's eye view), we need to rotate it
    to look forward horizontally. This is typically a 90-degree rotation
    around the X-axis.
    """
    # 90-degree rotation around X-axis to tilt camera from down to forward
    correction_angle = np.pi / 2  # 90 degrees
    correction_axis = np.array([1, 0, 0])  # X-axis
    return quat_from_angle_axis(correction_angle, correction_axis)

def create_human_rotations():
    """Create natural human-like rotations with proper gravity alignment
    
    This function creates rotations that:
    1. First correct any default camera orientation issues
    2. Keep the camera upright (Y-axis aligned with world up)
    3. Rotate horizontally (yaw around Y-axis)
    4. Apply pitch while maintaining upright orientation
    
    Modified to only generate "back" direction images.
    """
    rotations = []
    rotation_names = []
    
    # Get the base correction quaternion
    base_correction = correct_camera_orientation_quaternion()
    
    # Only back direction (180 degrees)
    yaw_angle = 180
    yaw_name = "back"
    
    # Level view (pitch = 0) - back_level
    yaw_rad = np.radians(yaw_angle)
    yaw_quat = quat_from_angle_axis(yaw_rad, np.array([0, 1, 0]))
    combined_quat = yaw_quat * base_correction
    rotations.append(combined_quat)
    rotation_names.append(f"{yaw_name}_level")
    
    # Add pitch variants for back direction
    pitch_angles = [15, -15]  # Looking up and down
    pitch_names = ["up", "down"]
    
    for pitch_deg, pitch_name in zip(pitch_angles, pitch_names):
        pitch_rad = np.radians(pitch_deg)
        
        # Create individual rotations
        yaw_quat = quat_from_angle_axis(yaw_rad, np.array([0, 1, 0]))
        pitch_quat = quat_from_angle_axis(pitch_rad, np.array([1, 0, 0]))
        
        # Combine: base correction, then yaw, then pitch
        combined_quat = yaw_quat * pitch_quat * base_correction
        
        rotations.append(combined_quat)
        rotation_names.append(f"{yaw_name}_{pitch_name}")
    
    return rotations, rotation_names

def verify_camera_orientation(agent, expected_direction_name):
    """Helper function to verify camera is looking in the expected direction"""
    state = agent.get_state()
    
    # Get the rotation quaternion
    rot_q = state.rotation
    
    # The camera's default forward is [0, 0, -1] in its local frame
    forward_local = np.array([0, 0, -1])
    
    # Rotate to world coordinates
    forward_world = quaternion.rotate_vectors(rot_q, forward_local)
    forward_world = forward_world / np.linalg.norm(forward_world)
    
    # For level views, Y component should be near zero
    if "level" in expected_direction_name:
        if abs(forward_world[1]) > 0.2:
            print(f"  ⚠ Camera not level! Y-component: {forward_world[1]:.3f}")
    
    # Check if the camera is looking mostly horizontally (not down at floor)
    if forward_world[1] < -0.7:  # Y negative means looking down
        print(f"  ⚠ Camera looking DOWN! Forward vector: {forward_world}")
        return False
    
    return True

sim = None
total_valid_images = 0

for scene_path in SCENE_FILES:
    scene_name = os.path.basename(scene_path).replace('.glb', '')
    print(f"\n{'='*60}")
    print(f"Processing scene: {scene_name}")
    print(f"{'='*60}")
    
    output_dir_for_scene = os.path.join(BASE_OUTPUT_DIR, scene_name)
    os.makedirs(output_dir_for_scene, exist_ok=True)

    if sim is not None:
        sim.close()
    
    try:
        cfg = make_sim_config(scene_path)
        sim = habitat_sim.Simulator(cfg)
    except Exception as e:
        print(f"Failed to load scene {scene_name}: {e}")
        continue
    
    # Generate or load navmesh
    if not sim.pathfinder.is_loaded:
        print("NavMesh not found. Generating a new one...")
        try:
            navmesh_settings = NavMeshSettings()
            navmesh_settings.set_defaults()
            navmesh_settings.agent_height = AGENT_HEIGHT
            navmesh_settings.agent_radius = 0.3
            navmesh_settings.agent_max_climb = 0.2
            navmesh_settings.agent_max_slope = 30.0
            sim.recompute_navmesh(sim.pathfinder, navmesh_settings)
            print("NavMesh generation complete.")
        except Exception as e:
            print(f"NavMesh generation failed: {e}")
            continue
    
    if not sim.pathfinder.is_loaded:
        print(f"ERROR: Failed to generate NavMesh for {scene_name}. Skipping scene.")
        continue

    print(f"Sampling viewpoints from the NavMesh...")
    
    # Get navmesh bounds
    navmesh_bounds = sim.pathfinder.get_bounds()
    print(f"NavMesh bounds: {navmesh_bounds}")
    
    # Find the floor level with stricter detection
    print("Detecting floor level...")
    sample_heights = []
    for _ in range(500):  # More samples for better floor detection
        sample_point = sim.pathfinder.get_random_navigable_point()
        sample_heights.append(sample_point[1])
    
    sample_heights.sort()
    # Use 5th percentile to find true ground floor (excludes furniture surfaces)
    floor_level = sample_heights[int(len(sample_heights) * 0.05)]
    height_tolerance = 0.1  # Stricter tolerance to exclude furniture surfaces
    
    print(f"Detected floor level: {floor_level:.3f}m")
    print(f"Eye level will be: {floor_level + AGENT_HEIGHT:.3f}m")
    
    # Get navigable points at floor level
    all_viewpoints = []
    attempts = 0
    max_attempts = NUM_VIEWPOINTS_PER_SCENE * 50
    
    while len(all_viewpoints) < NUM_VIEWPOINTS_PER_SCENE and attempts < max_attempts:
        point = sim.pathfinder.get_random_navigable_point()
        
        # Only accept points at floor level
        if abs(point[1] - floor_level) > height_tolerance:
            attempts += 1
            continue
        
        # Check minimum distance from existing points
        if len(all_viewpoints) == 0:
            all_viewpoints.append(point)
        else:
            min_distance = min([np.linalg.norm(point - existing) for existing in all_viewpoints])
            if min_distance > 1.5:
                all_viewpoints.append(point)
        
        attempts += 1

    if not all_viewpoints:
        print(f"No valid floor-level viewpoints found for {scene_name}. Skipping.")
        continue
    
    print(f"Found {len(all_viewpoints)} viewpoints")

    # Create human-like rotations with correction for camera orientation
    human_rotations, rotation_names = create_human_rotations()
    
    agent = sim.initialize_agent(0)
    agent_state = habitat_sim.AgentState()
    scene_valid_images = 0
    scene_total_attempts = 0
    orientation_warnings = 0

    for i, floor_point in enumerate(all_viewpoints):
        print(f"\nViewpoint {i+1}/{len(all_viewpoints)}")
        
        for j, (rotation, rotation_name) in enumerate(zip(human_rotations, rotation_names)):
            # Set agent position at eye height
            agent_position = np.array(floor_point, dtype=np.float32)
            # Use consistent floor level for all points to ensure uniform eye height
            agent_position[1] = floor_level + AGENT_HEIGHT
            
            # Set agent state
            agent_state.position = agent_position
            agent_state.rotation = rotation
            agent_state.sensor_states = {}
            agent.set_state(agent_state)
            
            # Verify orientation for first few captures
            if i == 0 and j < 3:
                is_correct = verify_camera_orientation(agent, rotation_name)
                if not is_correct:
                    orientation_warnings += 1
                    print(f"  Orientation check failed for {rotation_name}")
            
            try:
                observations = sim.get_sensor_observations()
                if 'rgb' not in observations:
                    continue
                    
                rgb_array = observations["rgb"]
                
                if len(rgb_array.shape) == 3 and rgb_array.shape[2] >= 3:
                    rgb_array = rgb_array[..., :3]
                else:
                    continue
                
                scene_total_attempts += 1
                
                # Validate and save the image
                if is_valid_image(rgb_array):
                    rgb_img = Image.fromarray(rgb_array.astype(np.uint8), "RGB")
                    rgb_filepath = os.path.join(output_dir_for_scene, f"point_{i:02d}_{rotation_name}.png")
                    rgb_img.save(rgb_filepath)
                    scene_valid_images += 1
                    total_valid_images += 1
                    
                    if scene_valid_images <= 3:
                        print(f"  ✓ Saved: {rotation_name}")
                    
            except Exception as e:
                print(f"  ERROR: {e}")
                continue
    
    if orientation_warnings > 0:
        print(f"\n⚠ WARNING: {orientation_warnings} orientation issues detected!")
        print("  The camera may still be looking down. You may need to adjust")
        print("  the correction angle in correct_camera_orientation_quaternion()")
    
    print(f"\n✅ Scene {scene_name} complete!")
    print(f"   Valid images: {scene_valid_images}/{scene_total_attempts}")

if sim is not None:
    sim.close()

print(f"\n{'='*60}")
print(f"🎉 All scenes processed!")
print(f"   Total valid images: {total_valid_images}")
print(f"{'='*60}")

# Additional debugging note
print("\nNOTE: If images are still showing top-down view, try adjusting:")
print("  1. The correction angle in correct_camera_orientation_quaternion()")
print("  2. Try negative angles (-np.pi/2) if the rotation is opposite")
print("  3. Try rotating around Z-axis instead of X-axis")