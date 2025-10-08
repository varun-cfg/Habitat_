import os
import habitat_sim
import numpy as np
from PIL import Image
from habitat_sim.nav import NavMeshSettings
from habitat_sim.utils.common import quat_from_angle_axis, quat_rotate_vector

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
    
    # Check if image is too uniform (like a solid wall very close up)
    if variance < MIN_VARIANCE_THRESHOLD:
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
    # CRITICAL: Proper gravity-aligned camera configuration
    sensor_spec = habitat_sim.CameraSensorSpec()
    sensor_spec.uuid = "rgb"
    sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
    sensor_spec.resolution = [settings["height"], settings["width"]]
    # Sensor at agent's eye position (no offset)
    sensor_spec.position = [0.0, 0.0, 0.0]
    # CRITICAL FIX: Apply -90° roll to correct the 90° CW rotation issue
    # Habitat-Sim coordinate system requires -90° roll for proper human perspective
    # Orientation: [pitch, yaw, roll] in radians
    sensor_spec.orientation = [0.0, 0.0, -np.pi/2]  # -90° roll correction
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

def quat_from_two_vectors(v1, v2):
    """Create a quaternion that rotates from v1 to v2"""
    v1 = v1 / np.linalg.norm(v1)
    v2 = v2 / np.linalg.norm(v2)
    
    cos_theta = np.dot(v1, v2)
    
    # Check if vectors are parallel
    if cos_theta > 0.9999:
        return np.quaternion(1, 0, 0, 0)
    
    # Check if vectors are anti-parallel  
    if cos_theta < -0.9999:
        # Find an orthogonal vector
        axis = np.array([1, 0, 0]) if abs(v1[0]) < 0.9 else np.array([0, 1, 0])
        axis = np.cross(v1, axis)
        axis = axis / np.linalg.norm(axis)
        return quat_from_angle_axis(np.pi, axis)
    
    axis = np.cross(v1, v2)
    axis = axis / np.linalg.norm(axis)
    angle = np.arccos(np.clip(cos_theta, -1, 1))
    
    return quat_from_angle_axis(angle, axis)

def create_human_rotations():
    """Create human perspective rotations ensuring proper gravity alignment
    
    HUMAN PERSPECTIVE REQUIREMENTS:
    1. Agent stands upright (feet on floor, head toward ceiling)
    2. Camera at human eye height (1.6m above floor)
    3. Looking horizontally or with slight up/down tilt
    4. Y-axis always points UP (against gravity)
    
    Habitat-sim coordinate system:
    - +Y axis: UP (opposite of gravity direction)
    - +X axis: RIGHT  
    - -Z axis: FORWARD (default camera look direction)
    """
    rotations = []
    rotation_names = []
    
    # 8 cardinal and intercardinal directions (horizontal looking)
    # These represent a person standing upright and turning to look in different directions
    yaw_angles = [0, 45, 90, 135, 180, 225, 270, 315]
    yaw_names = ["forward", "ne", "right", "se", "back", "sw", "left", "nw"]
    
    for yaw, name in zip(yaw_angles, yaw_names):
        # Pure horizontal rotation around Y-axis (world up)
        # This simulates a person turning their body while standing upright
        yaw_rad = np.radians(yaw)
        rotation = quat_from_angle_axis(yaw_rad, np.array([0, 1, 0]))
        rotations.append(rotation)
        rotation_names.append(f"{name}_0deg")
    
    # Add pitch variants for natural human head movements
    # A person can look up/down while keeping their body upright
    pitch_angles = [15, -15]  # +15° = look up, -15° = look down
    pitch_names = ["up", "down"]
    
    for pitch, pitch_name in zip(pitch_angles, pitch_names):
        # Key directions where humans commonly look up/down
        for yaw, yaw_name in [(0, "forward"), (90, "right"), (270, "left")]:
            # Step 1: Rotate body horizontally (yaw around world Y-axis)
            yaw_rad = np.radians(yaw)
            yaw_quat = quat_from_angle_axis(yaw_rad, np.array([0, 1, 0]))
            
            # Step 2: Tilt head up/down (pitch around local X-axis)
            # After yaw rotation, X-axis is the new "right" direction
            pitch_rad = np.radians(pitch)
            pitch_quat = quat_from_angle_axis(pitch_rad, np.array([1, 0, 0]))
            
            # Combine rotations: body yaw first, then head pitch
            # This maintains upright posture while allowing head tilt
            combined_rotation = yaw_quat * pitch_quat
            
            rotations.append(combined_rotation)
            rotation_names.append(f"{yaw_name}_{pitch_name}")
    
    return rotations, rotation_names

sim = None
total_valid_images = 0

for scene_path in SCENE_FILES:
    scene_name = os.path.basename(scene_path).replace('.glb', '')
    print(f"--- Processing scene: {scene_name} ---")
    
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
            # Adjust settings for better floor detection
            navmesh_settings.agent_height = AGENT_HEIGHT  # Human height
            navmesh_settings.agent_radius = 0.3  # Reasonable human radius
            navmesh_settings.agent_max_climb = 0.2  # Maximum step height (20cm)
            navmesh_settings.agent_max_slope = 30.0  # Maximum walkable slope in degrees
            sim.recompute_navmesh(sim.pathfinder, navmesh_settings)
            print("NavMesh generation complete.")
        except Exception as e:
            print(f"NavMesh generation failed: {e}")
            continue
    
    if not sim.pathfinder.is_loaded:
        print(f"ERROR: Failed to generate NavMesh for {scene_name}. Skipping scene.")
        continue

    print(f"Sampling viewpoints from the NavMesh...")
    
    # Get navmesh bounds to understand the scene
    navmesh_bounds = sim.pathfinder.get_bounds()
    print(f"NavMesh bounds: {navmesh_bounds}")
    
    # Find the lowest navigable height (the actual floor level)
    # Sample many points to find the true floor level
    print("Detecting floor level...")
    sample_heights = []
    for _ in range(100):
        sample_point = sim.pathfinder.get_random_navigable_point()
        sample_heights.append(sample_point[1])
    
    sample_heights.sort()
    # Use the 10th percentile as floor level to avoid outliers
    floor_level = sample_heights[10]  
    height_tolerance = 0.3  # Only accept points within 30cm of floor level
    
    print(f"Detected floor level: {floor_level:.3f}m")
    print(f"Height tolerance: ±{height_tolerance}m")
    
    # Get navigable points at floor level only, ensuring they're properly spaced
    all_viewpoints = []
    attempts = 0
    max_attempts = NUM_VIEWPOINTS_PER_SCENE * 50  # More attempts since we're filtering
    
    while len(all_viewpoints) < NUM_VIEWPOINTS_PER_SCENE and attempts < max_attempts:
        point = sim.pathfinder.get_random_navigable_point()
        
        # Only accept points that are at floor level (not elevated surfaces or stairs)
        if abs(point[1] - floor_level) > height_tolerance:
            attempts += 1
            continue
        
        # Check if point is valid and not too close to existing points
        if len(all_viewpoints) == 0:
            all_viewpoints.append(point)
            print(f"✓ Point {len(all_viewpoints)}: height={point[1]:.3f}m")
        else:
            # Ensure minimum distance between viewpoints
            min_distance = min([np.linalg.norm(point - existing) for existing in all_viewpoints])
            if min_distance > 1.5:  # At least 1.5 meters apart
                all_viewpoints.append(point)
                print(f"✓ Point {len(all_viewpoints)}: height={point[1]:.3f}m")
        
        attempts += 1

    if not all_viewpoints:
        print(f"No valid floor-level viewpoints found for {scene_name}. Skipping.")
        continue
    
    print(f"Found {len(all_viewpoints)} floor-level viewpoints after {attempts} attempts")

    # Create human-like rotations
    human_rotations, rotation_names = create_human_rotations()
    
    agent = sim.initialize_agent(0)
    agent_state = habitat_sim.AgentState()
    scene_valid_images = 0
    scene_total_attempts = 0

    for i, floor_point in enumerate(all_viewpoints):
        print(f"\nProcessing viewpoint {i+1}/{len(all_viewpoints)}")
        print(f"  Floor position: [{floor_point[0]:.2f}, {floor_point[1]:.2f}, {floor_point[2]:.2f}]")
        
        for j, (rotation, rotation_name) in enumerate(zip(human_rotations, rotation_names)):
            # HUMAN PERSPECTIVE SETUP:
            # 1. Position: Stand on floor at human eye height (1.6m above ground)
            # 2. Rotation: Body orientation + head direction (gravity-aligned)
            # 3. Sensor: Inherits agent orientation with roll correction applied
            
            # Set human eye height position
            agent_position = np.array(floor_point, dtype=np.float32)
            agent_position[1] = floor_point[1] + AGENT_HEIGHT  # 1.6m above floor
            
            # Apply human-like rotation (upright body + head direction)
            agent_state.position = agent_position
            agent_state.rotation = rotation  # Combined yaw + pitch quaternion
            agent_state.sensor_states = {}
            agent.set_state(agent_state)
            
            # Verification: Check if position was set correctly
            actual_state = agent.get_state()
            height_diff = abs(actual_state.position[1] - (floor_point[1] + AGENT_HEIGHT))
            
            if height_diff > 0.1:
                print(f"  ⚠ Height mismatch for {rotation_name}: expected {floor_point[1] + AGENT_HEIGHT:.2f}, got {actual_state.position[1]:.2f}")
            
            # Debug output for first capture
            if i == 0 and j == 0:
                print(f"  ✓ First capture setup:")
                print(f"    Floor height: {floor_point[1]:.3f}m")
                print(f"    Camera height: {actual_state.position[1]:.3f}m (floor + {AGENT_HEIGHT}m)")
                print(f"    Rotation: {actual_state.rotation}")
                print(f"    Direction: {rotation_name}")
            
            try:
                observations = sim.get_sensor_observations()
                if 'rgb' not in observations:
                    continue
                    
                rgb_array = observations["rgb"]
                
                # Ensure we have the right format
                if len(rgb_array.shape) == 3 and rgb_array.shape[2] >= 3:
                    rgb_array = rgb_array[..., :3]  # Take only RGB channels
                else:
                    continue
                
                scene_total_attempts += 1
                
                # Validate the image
                if is_valid_image(rgb_array):
                    rgb_img = Image.fromarray(rgb_array.astype(np.uint8), "RGB")
                    rgb_filepath = os.path.join(output_dir_for_scene, f"point_{i:02d}_{rotation_name}.png")
                    rgb_img.save(rgb_filepath)
                    scene_valid_images += 1
                    total_valid_images += 1
                    print(f"✓ Saved valid image: point_{i:02d}_{rotation_name}")
                else:
                    print(f"× Skipped invalid image at point {i}, rotation {rotation_name}")
                    
            except Exception as e:
                print(f"Error capturing image at point {i}, rotation {rotation_name}: {e}")
                continue
            
    print(f"✅ Scene {scene_name} complete! Valid images: {scene_valid_images}/{scene_total_attempts}")

if sim is not None:
    sim.close()

print(f"\n🎉 All scenes processed! Total valid images captured: {total_valid_images}")