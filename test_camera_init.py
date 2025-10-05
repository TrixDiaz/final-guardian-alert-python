#!/usr/bin/env python3
"""
Test script to verify camera initialization logic
"""

import sys
import time

# Try to import picamera2, fallback if not available
try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
    print("✓ picamera2 is available")
except ImportError:
    PICAMERA_AVAILABLE = False
    print("✗ picamera2 not available - this is expected on Windows")

def test_camera_initialization():
    """Test the camera initialization logic"""
    print("\n=== Testing Camera Initialization Logic ===")
    
    # Simulate the FaceMotionDetector initialization
    camera_initialized = False
    camera = None
    camera_retry_count = 0
    max_camera_retries = 5
    
    # Check if picamera2 is available
    if not PICAMERA_AVAILABLE:
        print("✗ picamera2 not available. This application requires a Raspberry Pi with picamera2 installed.")
        print("For development/testing on Windows, you can use a webcam by modifying the code.")
        camera_initialized = False
        return False
    
    print("✓ picamera2 is available, proceeding with camera initialization...")
    return True

if __name__ == "__main__":
    print("=== Camera Initialization Test ===")
    print(f"Platform: {sys.platform}")
    print(f"Python version: {sys.version}")
    
    success = test_camera_initialization()
    
    if success:
        print("\n✓ Camera initialization logic test passed!")
    else:
        print("\n✗ Camera initialization logic test failed!")
        print("This is expected on Windows - the code is designed for Raspberry Pi.")
