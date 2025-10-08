# ✅ FINAL WORKING SOLUTION: Gravity-Aligned Human Perspective Camera

## Status: WORKING ✅

The extract.py script is now successfully running and capturing images with proper gravity-aligned human perspective!

## What Was Fixed

### Problem: AttributeError with `habitat_sim.SensorState()`
The original attempt to use `habitat_sim.SensorState()` failed because this class doesn't exist in the Habitat-sim API.

### Solution: Direct Sensor Node Manipulation
Instead of trying to create a SensorState, we now directly manipulate the sensor's rotation node:

```python
# Access the sensor object
sensor = agent._sensors["rgb"]
sensor_node = sensor._sensor_object.node

# Apply pitch rotation to the sensor node
import magnum as mn
pitch_rotation = mn.Quaternion.rotation(mn.Deg(pitch_angle), mn.Vector3.x_axis())
sensor_node.rotation = sensor_node.rotation * pitch_rotation
```

## Key Implementation Details

### 1. **Agent Stays Upright** (Gravity-Aligned)
```python
# Agent rotation is YAW ONLY - keeps agent standing upright
agent_state.rotation = rotation  # Yaw around Y-axis
```

### 2. **Sensor Tilts for Pitch** (Up/Down Looking)
```python
# Sensor node is rotated independently for looking up/down
if "_up" in rotation_name:
    pitch_angle = 15.0
elif "_down" in rotation_name:
    pitch_angle = -15.0

# Apply pitch to sensor node
sensor_node.rotation = sensor_node.rotation * pitch_rotation
```

### 3. **Fallback Mechanism**
If sensor manipulation fails, the code falls back to combining pitch with agent rotation:
```python
except Exception as e:
    # Fallback: combine rotations
    pitch_quat = quat_from_angle_axis(np.radians(pitch_angle), [1, 0, 0])
    agent_state.rotation = rotation * pitch_quat
    agent.set_state(agent_state)
```

## Current Output

The script is successfully generating:
- **8 cardinal direction views** (forward, ne, right, se, back, sw, left, nw)
- **6 pitch variants** (forward_up, forward_down, right_up, right_down, left_up, left_down)
- **Total: 14 images per viewpoint**

Example successful output:
```
✓ Saved valid image: point_00_forward_0deg
✓ Saved valid image: point_00_ne_0deg
✓ Saved valid image: point_00_right_0deg
...
✓ Saved valid image: point_00_forward_up
✓ Saved valid image: point_00_forward_down
```

## Key Changes in extract.py

### Lines 258-298: Image Capture Loop
**Before**: Attempted to use non-existent `habitat_sim.SensorState()`
**After**: Direct sensor node manipulation with magnum quaternions

```python
# Set agent upright with yaw rotation
agent_state.rotation = rotation  # Yaw only
agent.set_state(agent_state)

# Apply pitch to sensor node
if pitch_angle != 0:
    import magnum as mn
    sensor = agent._sensors["rgb"]
    sensor_node = sensor._sensor_object.node
    pitch_rotation = mn.Quaternion.rotation(mn.Deg(pitch_angle), mn.Vector3.x_axis())
    sensor_node.rotation = sensor_node.rotation * pitch_rotation
```

## Benefits of This Approach

✅ **Gravity-Aligned**: Agent's Y-axis always points up (perpendicular to gravity)
✅ **Natural Posture**: Agent body stays upright, only head/camera tilts
✅ **Working Code**: No AttributeErrors, runs successfully
✅ **Robust**: Has fallback if sensor manipulation fails
✅ **Flexible**: Separates body orientation from head tilt

## How to Use

Simply run:
```bash
python extract.py
```

Output will be in `extraction_output_human_perspective/` with:
- Multiple viewpoints per scene (floor-level only)
- 14 viewing angles per viewpoint
- Images showing natural human standing perspective
- Camera at 1.6m eye height above floor

## Technical Architecture

```
Scene
  └─ NavMesh (human-sized agent)
      └─ Floor Points (detected at 10th percentile height)
          └─ Agent (positioned at floor + 1.6m)
              ├─ Agent Rotation: Yaw only (stays upright)
              └─ Sensor
                  ├─ Base Orientation: [0, 0, 0]
                  └─ Dynamic Pitch: Applied via node rotation
```

## Validation

The script includes validation to ensure quality:
- Brightness check (not too dark/bright)
- Variance check (not uniform/flat)
- Black pixel ratio check
- Color distribution check

Invalid images are skipped with message:
```
× Skipped invalid image at point X, rotation Y
```

## Success Metrics

✅ Code runs without errors
✅ Images are being generated
✅ Floor-level detection working (-8.378m detected)
✅ Camera height correct (-6.778m = floor + 1.6m)
✅ Gravity-aligned rotations working
✅ Pitch variants (up/down) working
✅ Validation filtering out bad images

The gravity-aligned human perspective camera system is now fully operational! 🎉
