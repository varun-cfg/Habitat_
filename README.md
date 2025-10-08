# Project Documentation

This document provides a summary of the image extraction process and the key technical solutions implemented to achieve a gravity-aligned, human-perspective camera.

## Objective
Generate images from the perspective of a human standing upright in the scene, looking around naturally.

## Key Features and Fixes

### 1. Gravity-Aligned Human Perspective
- **Problem**: Initial images were rotated, and the agent was not always upright.
- **Solution**: A hybrid approach was implemented:
    - The **agent's rotation** is restricted to **yaw only** (turning left/right around the vertical Y-axis). This ensures the agent's body is always upright and aligned with gravity.
    - **Pitch** (looking up/down) is handled by directly manipulating the **sensor's orientation**, keeping the agent's body stable.
- **Code Reference**: `create_human_rotations()` and the main capture loop in `extract.py`.

### 2. Accurate Floor-Level Positioning
- **Problem**: The camera was sometimes positioned on elevated surfaces, walls, or stairs.
- **Solution**:
    1.  **Floor Level Detection**: The script samples hundreds of points to statistically determine the true floor level, avoiding outliers like furniture or small steps.
    2.  **Point Filtering**: Only navigable points within a small tolerance (e.g., ±30cm) of the detected floor level are used as viewpoints.
- **Code Reference**: Floor detection and viewpoint sampling logic in `extract.py`.

### 3. Human Eye Height
- **Problem**: The camera was not at a realistic height.
- **Solution**: The agent is consistently positioned at `floor_level + 1.6` meters, simulating the average human eye height.
- **Code Reference**: Agent state setup in the main capture loop in `extract.py`.

### 4. Camera Roll Correction
- **Problem**: A persistent 90-degree rotation was observed in the output images, a known characteristic of Habitat-sim's rendering pipeline.
- **Solution**: A **-90 degree roll correction** is applied to the sensor's orientation. This was a critical single-line fix that corrected the final image orientation.
- **Code Reference**: `sensor_spec.orientation` in `make_sim_config()` in `extract.py`.

### 5. Viewpoint Selection: Hybrid Grid-Clustering
- **Problem**: Random sampling could lead to clustered viewpoints, missing entire rooms.
- **Solution**: A hybrid approach is used:
    1. A dense cloud of points is sampled.
    2. These points are grouped into grid cells.
    3. The centers of these cells are then clustered to identify "rooms".
    4. The final viewpoints are the navigable points closest to the center of each room cluster.
- **This ensures a more even distribution of viewpoints across the entire scene.**
- **Code Reference**: The "Hybrid Grid-Clustering Approach" section in `extract.py`.

## How to Run the Extraction

1.  **Ensure Dependencies are Installed**: Make sure `habitat-sim` and other required libraries are in the environment.
2.  **Execute the Script**:
    ```bash
    python extract.py
    ```
3.  **Output**: Images will be saved in the `extraction_output_human_perspective/` directory, organized by scene name.

## Configuration
Key parameters can be adjusted at the top of `extract.py`:
- `SCENE_FILES`: List of scene files to process.
- `AGENT_HEIGHT`: The simulated human eye height.
- `NUM_VIEWPOINTS_PER_SCENE`: The target number of viewpoints per scene.
- `horizontal_directions`: The angles for horizontal camera rotations.

This consolidated approach ensures the generation of high-quality, realistic images that accurately reflect a human's perspective within the simulated environments.
