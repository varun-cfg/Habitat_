# Camera Orientation Fix - Based on Habitat-Sim Documentation

## Problem Analysis
The attached image shows the scene rotated 90 degrees - the floor appears as a vertical wall. This indicates a fundamental coordinate system or rotation issue.

## Solution Implemented

### 1. Proper Quaternion-Based Rotations
Following the [Habitat-Sim Image Extractor documentation](https://aihabitat.org/docs/habitat-sim/image-extractor), I've updated the code to use **proper quaternion rotations** that combine yaw and pitch:

```python
def create_human_rotations():
    """Create rotation quaternions that combine yaw and pitch properly"""
    
    #  8 horizontal directions (level with horizon)
    yaw_angles = [0, 45, 90, 135, 180, 225, 270, 315]
    for yaw in yaw_angles:
        yaw_rad = np.radians(yaw)
        # Rotate around Y-axis (up) for horizontal direction
        rotation = quat_from_angle_axis(yaw_rad, np.array([0, 1, 0]))
    
    # For looking up/down: combine yaw + pitch
    for yaw in [0, 90, 270]:  # forward, right, left
        for pitch in [15, -15]:  # up, down
            # First yaw, then pitch
            yaw_quat = quat_from_angle_axis(np.radians(yaw), np.array([0, 1, 0]))
            pitch_quat = quat_from_angle_axis(np.radians(pitch), np.array([1, 0, 0]))
            combined_rotation = yaw_quat * pitch_quat
```

### 2. Direct Agent State Rotation
Instead of manipulating sensor nodes (which was causing accumulation issues), the code now:
1. Sets agent position to floor + 1.6m (human eye height)
2. Sets agent rotation to the full combined quaternion
3. Sensor uses default `[0,0,0]` orientation and inherits agent rotation

```python
agent_state.position = floor_position + [0, 1.6, 0]
agent_state.rotation = rotation  # Full quaternion (yaw + pitch combined)
agent.set_state(agent_state)
```

### 3. Clean Sensor Configuration
```python
sensor_spec.position = [0.0, 0.0, 0.0]  # At agent eye position
sensor_spec.orientation = [0.0, 0.0, 0.0]  # Identity - inherits agent rotation
```

## Key Changes from Previous Approach

| Previous (Incorrect) | Current (Correct) |
|---------------------|-------------------|
| Separate yaw (agent) + pitch (sensor node) | Combined yaw+pitch quaternion |
| Sensor node manipulation with accumulation | Direct agent state rotation |
| Multiple rotation applications | Single quaternion per capture |

## Coordinate System Reference
- **+Y axis**: UP (opposite of gravity)
- **+X axis**: RIGHT
- **-Z axis**: FORWARD (default camera direction)

## Testing Required

Please verify the newly generated images in:
```
extraction_output_human_perspective/
```

**Check for:**
1. ✅ Floor is horizontal (not vertical/sideways)
2. ✅ Walls are vertical
3. ✅ Objects have correct orientation (not rotated 90°)
4. ✅ Human perspective (standing upright, looking from ~1.6m height)

## If Images Still Incorrect

If the orientation is still wrong, we may need to:
1. Add a sensor roll correction (`sensor_spec.orientation = [0, 0, roll_angle]`)
2. Investigate scene-specific coordinate system issues
3. Check if the GLB models have non-standard up-axis definitions

## Files Modified
- `extract.py`: Lines 100-152 (rotation creation), Lines 78-84 (sensor config), Lines 260-273 (capture loop)

## Run Extraction
```bash
python extract.py
```

Expected output: 125 images across both scenes with proper human perspective orientation.
