# Sensor Rotation Accumulation Fix

## Problem
Images were being captured with incorrect orientations (90-degree rotations) because sensor rotations were accumulating across iterations. Each pitch adjustment was being multiplied with the previous rotation instead of being set fresh.

## Root Cause
The code was applying pitch rotations like this:
```python
sensor_node.rotation = sensor_node.rotation * pitch_rotation  # WRONG - accumulates!
```

This caused rotations to stack up across different viewpoints and directions.

## Solution
The fix involves two critical changes:

### 1. Reset Sensor Orientation Before Each Capture
```python
import magnum as mn
sensor = sim._sensors["rgb"]  # Note: sim._sensors, not agent._sensors
sensor_node = sensor._sensor_object.node
# Reset to identity (level with horizon)
sensor_node.rotation = mn.Quaternion.identity_init()
```

### 2. Set Pitch Rotation Directly (Don't Multiply)
```python
if pitch_angle != 0:
    pitch_rotation = mn.Quaternion.rotation(
        mn.Deg(pitch_angle), 
        mn.Vector3.x_axis()
    )
    sensor_node.rotation = pitch_rotation  # Set directly, don't accumulate
```

## Key Points
- **Access pattern**: Use `sim._sensors["rgb"]._sensor_object.node`, not `agent._sensors["rgb"]`
- **Reset first**: Always reset to identity before applying new rotations
- **Direct assignment**: Use `=` not `*=` or `sensor_node.rotation * new_rotation`
- **Gravity alignment**: Agent rotation is yaw-only (keeps upright), pitch is sensor-only

## Results
After the fix:
- ✅ 125 images generated successfully
- ✅ Correct dimensions (640×480)
- ✅ Proper gravity alignment (floor is floor, not walls)
- ✅ No rotation accumulation artifacts
- ✅ Reasonable brightness values (197-236 mean)

## File Modified
- `extract.py` lines 260-305: Sensor orientation reset and pitch application

## Test Command
```bash
python extract.py
```

Expected output: Images with proper human perspective, standing on floor, gravity-aligned view.
