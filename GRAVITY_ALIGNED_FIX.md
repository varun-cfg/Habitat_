# GRAVITY-ALIGNED FIX: Complete Solution

## The Real Problem

After analyzing the images, the issue is that the agent/camera orientation isn't properly gravity-aligned. The camera needs to be:
1. **Upright** - Y-axis pointing up (opposite to gravity)
2. **Level with horizon** - Not tilted or rolled
3. **At human eye height** - 1.6m above floor

## Root Cause

The agent rotation quaternions we're creating don't maintain proper gravity alignment when combined with Habitat-sim's coordinate system. The sensor also needs correct orientation.

## Complete Solution

### Step 1: Agent Rotation (Yaw Only)
Agent should ONLY rotate around Y-axis (vertical/up). This keeps the agent standing upright.

```python
# Good: Yaw rotation only - agent stays upright
rotation = quat_from_angle_axis(yaw_radians, np.array([0, 1, 0]))

# Bad: Combining pitch with agent rotation tips the agent over
rotation = yaw_rotation * pitch_rotation  # DON'T DO THIS
```

### Step 2: Sensor Pitch (Up/Down Looking)
For looking up/down, apply pitch via sensor state, not agent rotation:

```python
if need_pitch:
    sensor_state = habitat_sim.SensorState()
    sensor_state.rotation = quat_from_angle_axis(pitch_radians, np.array([1, 0, 0]))
    agent_state.sensor_states = {"rgb": sensor_state}
```

### Step 3: Sensor Base Orientation
Sensor should have ZERO base orientation - it inherits from agent:

```python
sensor_spec.orientation = [0.0, 0.0, 0.0]  # Let agent control orientation
```

## Key Changes in extract.py

###  1. Sensor Configuration (Lines 75-86)
**Before**:
```python
sensor_spec.orientation = [0.0, 0.0, np.radians(-90)]  # Roll correction
```

**After**:
```python
sensor_spec.orientation = [0.0, 0.0, 0.0]  # No correction, agent controls
```

### 2. Rotation Generation (Lines 97-145)
**Before**: Mixed yaw+pitch in agent rotation
**After**: Yaw ONLY in agent rotation, pitch via sensor

### 3. Image Capture (Lines 255-280)
**Before**: All rotation in agent
**After**: 
- Agent rotation = yaw only (stays upright)
- Sensor rotation = pitch if needed

## Implementation

The fix is already applied in extract.py. Key points:

1. **Agent always upright**: Only yaw rotations
2. **Pitch via sensor**: Sensor state for up/down
3. **Floor-level positioning**: Proper height detection
4. **Gravity-aligned**: Y-axis always up

## Testing

Run:
```bash
python test_gravity_aligned.py
```

Expected results:
- Forward view shows interior (not ceiling/walls)
- Brightness 50-150 (varied scene)
- Variance >500 (not uniform)
- Horizon centered in level views

## Why This Works

**Gravity Alignment**: By keeping agent rotation to yaw-only, the agent's local Y-axis always points up (opposite to gravity). This ensures:
- Camera is level with horizon
- Vertical walls appear vertical
- Natural human standing perspective
- Proper up/down pitch via sensor

**Habitat-sim Convention**: 
- Agent rotation defines body orientation
- Sensor rotation is relative to agent
- Y-axis up = gravity-aligned
- Yaw around Y = horizontal turning (stays upright)
- Pitch around X = looking up/down (via sensor)

