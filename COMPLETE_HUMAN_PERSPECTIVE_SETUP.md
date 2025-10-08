# Human Perspective Image Extraction - Complete Setup

## Objective
Generate images from the perspective of a human standing upright in the scene, looking around naturally.

## Human Perspective Requirements

### ✅ Physical Position
- **Height**: 1.6m above floor level (average human eye height)
- **Stance**: Standing upright on navigable floor surfaces
- **Stability**: Feet planted on solid ground (no floating or elevated positions)

### ✅ Body Orientation  
- **Upright Posture**: Y-axis (up) always aligned with gravity
- **Natural Turning**: Body can rotate horizontally (yaw around Y-axis)
- **Head Movement**: Can look up/down while maintaining upright body posture

### ✅ Camera Configuration
- **Field of View**: 90° horizontal (natural human vision)
- **Resolution**: 640×480 pixels
- **Sensor Orientation**: -90° roll correction for proper gravity alignment

## Technical Implementation

### 1. Sensor Setup (Corrected Orientation)
```python
sensor_spec.orientation = [0.0, 0.0, -np.pi/2]  # -90° roll correction
sensor_spec.hfov = 90  # Natural human FOV
sensor_spec.resolution = [480, 640]  # [height, width]
```

### 2. Floor Detection & Positioning
```python
# Find true floor level using statistical sampling
sample_heights = [sim.pathfinder.get_random_navigable_point()[1] for _ in range(100)]
floor_level = sorted(sample_heights)[10]  # 10th percentile (avoids outliers)

# Position human at eye height
agent_position = floor_point + [0, AGENT_HEIGHT, 0]  # +1.6m above floor
```

### 3. Human-Like Rotations
```python
# Horizontal body rotations (standing upright, turning around)
yaw_quat = quat_from_angle_axis(yaw_radians, [0, 1, 0])  # Around world Y-axis

# Head tilt (looking up/down while body stays upright)  
pitch_quat = quat_from_angle_axis(pitch_radians, [1, 0, 0])  # Around local X-axis
combined = yaw_quat * pitch_quat  # Body first, then head
```

### 4. View Directions Generated
- **8 Horizontal**: forward, ne, right, se, back, sw, left, nw (0° pitch)
- **6 Tilted**: forward_up/down, right_up/down, left_up/down (±15° pitch)
- **Total**: 14 views per viewpoint

## Key Fixes Applied

### Issue 1: 90° Rotation
- **Problem**: Images rotated 90° (floor appeared vertical)
- **Solution**: Applied -90° roll correction to sensor orientation

### Issue 2: Non-Human Heights
- **Problem**: Camera at arbitrary heights (walls, ceiling, etc.)
- **Solution**: Statistical floor detection + fixed 1.6m eye height

### Issue 3: Improper Orientation
- **Problem**: Agent not gravity-aligned (tilted/sideways)
- **Solution**: Separate body yaw from head pitch rotations

## Expected Results

### ✅ Proper Human Perspective
- Floor appears horizontal at bottom of image
- Ceiling appears horizontal at top of image  
- Walls appear vertical
- Objects have correct upright orientation
- Natural human eye height viewpoint

### ✅ Image Quality
- Mean brightness: 150-250 (well-exposed)
- Sufficient detail variance (not uniform walls)
- Reasonable file sizes (20-100KB typical)
- No black/overexposed regions

## Output Structure
```
extraction_output_human_perspective/
├── 103997919_171031233/
│   ├── point_00_forward_0deg.png    # Viewpoint 0, looking forward
│   ├── point_00_right_0deg.png      # Viewpoint 0, looking right  
│   ├── point_00_forward_up.png      # Viewpoint 0, looking forward & up
│   └── ...
└── 102344250/
    └── ...
```

## Validation Checklist
- [ ] Floor is horizontal (not vertical/tilted)
- [ ] Human standing height perspective
- [ ] Natural head/body orientations
- [ ] Gravity points downward
- [ ] Objects appear upright
- [ ] Reasonable brightness levels
- [ ] Multiple viewpoints per scene

## Usage
```bash
python extract.py
```

Expected: ~100-150 images total across both scenes, all showing proper human perspective.