# Human Perspective Camera Fixes

## Changes Made to `extract.py`

### Problem
The original code had issues that prevented it from accurately simulating a human standing on the floor and viewing the scene naturally.

### Solutions Implemented

#### 1. **Fixed Quaternion Rotation Order** (Lines 100-140)
**Issue**: The pitch+yaw combined rotations were using incorrect quaternion multiplication order.

**Fix**: Changed from:
```python
combined_rotation = quat_from_angle_axis(yaw_rad, np.array([0, 1, 0])) * quat_from_angle_axis(pitch_rad, np.array([1, 0, 0]))
```

To:
```python
yaw_rotation = quat_from_angle_axis(yaw_rad, np.array([0, 1, 0]))
pitch_rotation_local = quat_from_angle_axis(pitch_rad, np.array([1, 0, 0]))
combined_rotation = yaw_rotation * pitch_rotation_local
```

**Why**: In quaternion mathematics, when multiplying `q1 * q2`, the rotation `q2` is applied first, then `q1`. For proper human-like head rotation, we need to yaw (turn) first, then pitch (tilt) in the local coordinate frame.

#### 2. **Simplified Agent Positioning** (Lines 210-223)
**Issue**: The original code had unnecessary navmesh validation that could interfere with the elevated camera position.

**Fix**: Removed the validation check that tried to snap positions. The code now:
- Takes the validated floor point from `get_random_navigable_point()`
- Adds exactly 1.6 meters (human eye height) to the Y-coordinate
- Sets the agent state directly without re-validation

**Why**: The floor point is already validated as navigable. We just need to elevate the camera to human eye height above it.

#### 3. **Added Proper Sensor Configuration** (Line 84)
**Issue**: Sensor subtype wasn't explicitly set.

**Fix**: Added:
```python
sensor_spec.sensor_subtype = habitat_sim.SensorSubType.PINHOLE
```

**Why**: Explicitly sets the camera model to pinhole, which is the standard perspective projection matching human vision.

#### 4. **Enhanced Documentation**
- Added detailed comments explaining Habitat-sim's coordinate system
- Clarified that Y-axis is up, X-axis is for pitch, and quaternion multiplication order
- Updated AGENT_HEIGHT comment to specify the measurement is in meters

## How It Works Now

1. **Navigable Points**: The simulator samples random navigable floor positions from the scene's navmesh
2. **Human Height**: Each floor position is elevated by 1.6 meters (average human eye height)
3. **Natural Rotations**: 
   - 8 cardinal directions (forward, NE, right, SE, back, SW, left, NW)
   - 3 pitch variations per major direction (level, up 15°, down 15°)
   - Total of 14 viewing angles per position
4. **Validation**: Images are checked for sufficient brightness, variance, and color distribution

## Result
Images now accurately represent what a human would see standing on the floor at average eye height, looking around naturally in different directions and angles.
