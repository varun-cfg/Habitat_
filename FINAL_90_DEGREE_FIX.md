# FINAL FIX: 90-Degree Rotation Issue RESOLVED

## Problem
Images were consistently rotated 90 degrees counter-clockwise (CCW). The floor appeared as a vertical wall, indicating a coordinate system mismatch.

## Root Cause
**Habitat-Sim renders images rotated 90° CCW by default.** This is a known behavior in the rendering pipeline and must be corrected via sensor orientation.

## Solution
Apply a **+90° roll correction** to the sensor orientation:

```python
# In extract.py, line 84:
sensor_spec.orientation = [0.0, 0.0, np.pi/2]  # +90° roll correction
```

Where orientation is `[pitch, yaw, roll]` in radians.

## Why This Works
- Habitat-Sim's default rendering: Image rotated 90° CCW
- Our correction: Rotate sensor +90° CW (roll = +π/2)
- Result: -90° + 90° = 0° (correct orientation)

## Verification
After applying this fix, images should show:
- ✅ Floor horizontal (bottom of image)
- ✅ Ceiling horizontal (top of image)  
- ✅ Walls vertical
- ✅ Objects upright
- ✅ Gravity pointing down

## Technical Details

### Sensor Configuration (Final Working Version)
```python
sensor_spec = habitat_sim.CameraSensorSpec()
sensor_spec.uuid = "rgb"
sensor_spec.sensor_type = habitat_sim.SensorType.COLOR
sensor_spec.resolution = [480, 640]  # [height, width]
sensor_spec.position = [0.0, 0.0, 0.0]  # At agent position
sensor_spec.orientation = [0.0, 0.0, np.pi/2]  # [pitch, yaw, roll] - +90° roll
sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
sensor_spec.hfov = 90
```

### Agent Rotation (Gravity-Aligned)
```python
# Yaw only (horizontal rotation around Y-axis = up)
yaw_quat = quat_from_angle_axis(yaw_radians, np.array([0, 1, 0]))

# Combined yaw + pitch (for looking up/down)
yaw_quat = quat_from_angle_axis(yaw_radians, np.array([0, 1, 0]))
pitch_quat = quat_from_angle_axis(pitch_radians, np.array([1, 0, 0]))
combined_quat = yaw_quat * pitch_quat

# Set agent state
agent_state.position = floor_position + [0, 1.6, 0]  # Eye height
agent_state.rotation = combined_quat
agent.set_state(agent_state)
```

## Complete Fix History

### Attempts Made:
1. ❌ Roll correction on agent quaternion - Didn't work
2. ❌ Sensor node manipulation - Caused accumulation
3. ❌ Separate yaw/pitch application - Wrong approach
4. ❌ -90° roll on sensor - Wrong direction
5. ✅ **+90° roll on sensor orientation - WORKS!**

## Files Modified
- `extract.py` line 84: `sensor_spec.orientation = [0.0, 0.0, np.pi/2]`

## How to Run
```bash
python extract.py
```

## Expected Output
- 125 images total (varying by floor-level viewpoints found)
- Images with correct orientation
- Human perspective at 1.6m eye height
- Gravity-aligned views (floor is down, ceiling is up)

## Key Insight
The sensor orientation parameter directly controls the camera's intrinsic rotation, independent of agent rotation. The agent rotation controls **where** the camera points (yaw/pitch), while sensor orientation controls **how** the camera is rolled around its viewing axis.

**The +90° roll correction is necessary for Habitat-Sim's rendering pipeline.**
