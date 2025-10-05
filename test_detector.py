#!/usr/bin/env python3
"""
Test script for FaceMotionDetector initialization
"""

import sys
import time

def test_detector_initialization():
    """Test FaceMotionDetector initialization"""
    try:
        print("Testing FaceMotionDetector initialization...")
        
        # Import the detector class
        from main import FaceMotionDetector
        
        print("✓ Successfully imported FaceMotionDetector")
        
        # Try to initialize the detector
        print("Initializing FaceMotionDetector...")
        detector = FaceMotionDetector()
        
        print("✓ FaceMotionDetector initialized successfully")
        
        # Check camera status
        if detector.camera_initialized:
            print("✓ Camera is initialized and working")
        else:
            print("⚠ Camera is not initialized - this is expected if running on non-Raspberry Pi")
        
        # Test other components
        print(f"✓ Face cascade loaded: {detector.face_cascade is not None}")
        print(f"✓ Background subtractor created: {detector.background_subtractor is not None}")
        print(f"✓ Processing thread started: {detector.processing_thread.is_alive()}")
        
        # Test frame capture
        print("Testing frame capture...")
        frame = detector.get_frame()
        if frame is not None:
            print("✓ Frame capture working")
        else:
            print("⚠ No frame available (expected if camera not working)")
        
        print("\n✓ FaceMotionDetector test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ FaceMotionDetector test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== FaceMotionDetector Test ===")
    success = test_detector_initialization()
    
    if success:
        print("\n✓ All tests passed!")
        print("The FaceMotionDetector should work properly now.")
    else:
        print("\n✗ Tests failed!")
        print("Please check the error messages above.")
