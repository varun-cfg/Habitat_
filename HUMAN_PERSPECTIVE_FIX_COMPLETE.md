# Human Perspective Camera - Complete Fix Documentation

## Problem
The original code was capturing images where the camera appeared to be:
1. Sticking to walls instead of standing on the floor
2. Positioned at ceiling level or elevated surfaces
3. Not at human eye height

## Root Causes Identified

### 1. **No Floor Level Filtering**
`sim.pathfinder.get_random_navigable_point()` returns points from the entire navigable mesh, which includes:
- Floor surfaces  
- Elevated platforms
- Stairs
- Wall-adjacent areas

**Solution**: Sample many points to detect the true floor level (10th percentile of heights), then only accept points within ±30cm of that level.

### 2. **Incorrect Navmesh Settings**
The navmesh was generated with default settings that didn't account for human dimensions.

**Solution**: Configure navmesh with human-appropriate parameters:
```python
navmesh_settings.agent_height = 1.6  # Human height
navmesh_settings.agent_radius = 0.3  # Human body radius
navmesh_settings.agent_max_climb = 0.2  # Max step height (20cm)
navmesh_settings.agent_max_slope = 30.0  # Max walkable slope
```

### 3. **Sensor Configuration**
The sensor configuration wasn't explicitly set for natural human vision.

**Solution**: Added proper sensor specifications:
```python
sensor_spec.hfov = 90  # 90° horizontal FOV (natural human vision)
sensor_spec.orientation = [0.0, 0.0, 0.0]  # Level horizon (Euler angles)
```

## Key Changes Made to `extract.py`

### Change 1: Floor Level Detection (Lines ~195-245)
```python
# Sample many points to find true floor level
sample_heights = []
for _ in range(100):
    sample_point = sim.pathfinder.get_random_navigable_point()
    sample_heights.append(sample_point[1])

sample_heights.sort()
floor_level = sample_heights[10]  # 10th percentile
height_tolerance = 0.3  # Only accept points within 30cm of floor

# Filter viewpoints to floor level only
while len(all_viewpoints) < NUM_VIEWPOINTS_PER_SCENE:
    point = sim.pathfinder.get_random_navigable_point()
    
    # Only accept floor-level points
    if abs(point[1] - floor_level) > height_tolerance:
        continue
    
    # Ensure minimum spacing between points
    if min_distance_to_existing_points > 1.5:
        all_viewpoints.append(point)
```

### Change 2: Improved Navmesh Generation (Lines ~167-177)
```python
navmesh_settings = NavMeshSettings()
navmesh_settings.set_defaults()
navmesh_settings.agent_height = AGENT_HEIGHT  # 1.6m
navmesh_settings.agent_radius = 0.3  # 30cm radius
navmesh_settings.agent_max_climb = 0.2  # 20cm max step
navmesh_settings.agent_max_slope = 30.0  # 30° max slope
sim.recompute_navmesh(sim.pathfinder, navmesh_settings)
```

### Change 3: Proper Camera Positioning (Lines ~255-272)
```python
# Position camera at human eye height above floor
agent_position = np.array(floor_point, dtype=np.float32)
agent_position[1] = floor_point[1] + AGENT_HEIGHT  # floor + 1.6m

agent_state.position = agent_position
agent_state.rotation = rotation  # Quaternion for direction
agent_state.sensor_states = {}  # Clear any overrides

agent.set_state(agent_state)
```

### Change 4: Enhanced Sensor Configuration (Lines ~75-84)
```python
sensor_spec = habitat_sim.CameraSensorSpec()
sensor_spec.uuid = "rgb"
sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
sensor_spec.resolution = [480, 640]
sensor_spec.position = [0.0, 0.0, 0.0]  # At agent position
sensor_spec.orientation = [0.0, 0.0, 0.0]  # Level with horizon
sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
sensor_spec.hfov = 90  # Natural human FOV
```

### Change 5: Better Rotation Documentation (Lines ~97-141)
Added comprehensive documentation of Habitat-sim's coordinate system:
- +Y axis: UP
- +X axis: RIGHT  
- -Z axis: FORWARD (default camera direction)
- Rotations use right-hand rule
- Quaternions properly combine yaw and pitch

## How It Works Now

1. **Load Scene**: Scene is loaded into Habitat-sim simulator
2. **Generate Navmesh**: Navmesh is created with human-appropriate dimensions
3. **Detect Floor Level**: Sample 100 random navigable points and use 10th percentile as floor level
4. **Sample Floor Points**: Only accept points within 30cm of floor level, spaced 1.5m+ apart
5. **Position Camera**: For each floor point:
   - Set X, Z from floor point (horizontal position)
   - Set Y = floor_point.y + 1.6m (human eye height)
6. **Set Orientation**: Apply quaternion rotation for desired viewing direction
7. **Capture Image**: Sensor is level with horizon, pointing in specified direction
8. **Validate**: Check brightness, variance, color distribution

## Result

Images now accurately represent what a 1.6m tall human would see while standing on navigable floor surfaces, looking around in natural directions (8 cardinal directions + up/down tilts).

## Testing

Run `test_human_fix.py` to verify:
- ✅ Camera height is exactly floor + 1.6m
- ✅ Horizon appears in middle of level views
- ✅ Look_up shows ceiling/upper areas
- ✅ Look_down shows more floor
- ✅ No tilting or rotation artifacts

## Configuration Options

In `extract.py`, you can adjust:
- `AGENT_HEIGHT = 1.6`: Change human eye height (meters)
- `NUM_VIEWPOINTS_PER_SCENE = 10`: Number of positions per scene
- `height_tolerance = 0.3`: How strict floor filtering is (meters)
- `min_distance = 1.5`: Minimum spacing between viewpoints (meters)
- `ENABLE_PHYSICS = False`: Enable if positioning issues persist
