#!/usr/bin/env python3
"""
Verify that our rotations are producing the expected results
"""

import numpy as np
from habitat_sim.utils.common import quat_from_angle_axis
import quaternion

def test_expected_rotations():
    """Test what rotations should produce based on your requirements"""
    
    print("=== EXPECTED ROTATION BEHAVIOR ===")
    print("If you want the agent to look at 4 walls from a room center:")
    print("- Should 0° look forward?")
    print("- Should 90° look right or left?") 
    print("- Should 180° look back?")
    print("- Should 270° look left or right?")
    print()
    
    # Current behavior (what we're getting)
    print("=== CURRENT BEHAVIOR ===")
    angles = [0, 90, 180, 270]
    names = ["forward", "left", "back", "right"]
    
    for angle, name in zip(angles, names):
        angle_rad = np.radians(angle)
        y_quat = quat_from_angle_axis(angle_rad, np.array([0, 1, 0]))
        
        # Default camera forward
        forward_local = np.array([0, 0, -1])
        forward_world = quaternion.rotate_vectors(y_quat, forward_local)
        
        print(f"{angle:3d}° ({name:7s}): {forward_world}")
    
    print()
    print("=== ALTERNATIVE: CLOCKWISE ROTATION ===") 
    print("If you want clockwise instead of counter-clockwise:")
    
    # Try negative angles (clockwise)
    alt_angles = [0, -90, -180, -270]  # or [0, 270, 180, 90]
    alt_names = ["forward", "right", "back", "left"]
    
    for angle, name in zip(alt_angles, alt_names):
        angle_rad = np.radians(angle)
        y_quat = quat_from_angle_axis(angle_rad, np.array([0, 1, 0]))
        
        forward_local = np.array([0, 0, -1])
        forward_world = quaternion.rotate_vectors(y_quat, forward_local)
        
        print(f"{angle:4d}° ({name:7s}): {forward_world}")

if __name__ == "__main__":
    test_expected_rotations()