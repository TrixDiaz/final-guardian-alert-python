#!/usr/bin/env python3
"""
Simple camera test script to diagnose picamera2 issues
"""

import sys
import time

def test_camera():
    """Test basic camera functionality"""
    try:
        print("Testing camera initialization...")
        from picamera2 import Picamera2
        
        # Initialize camera
        camera = Picamera2()
        print("✓ Camera object created successfully")
        
        # Get camera properties
        properties = camera.camera_properties
        print(f"✓ Camera properties: {properties}")
        
        # Test different configurations
        configs_to_test = [
            ("Default", camera.create_video_configuration()),
            ("RGB888", camera.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})),
            ("YUV420", camera.create_video_configuration(main={"size": (640, 480), "format": "YUV420"})),
        ]
        
        for config_name, config in configs_to_test:
            try:
                print(f"Testing {config_name} configuration...")
                camera.configure(config)
                print(f"✓ {config_name} configuration successful")
                
                # Start camera
                camera.start()
                print(f"✓ Camera started with {config_name}")
                
                # Capture a test frame
                frame = camera.capture_array()
                print(f"✓ Frame captured: shape={frame.shape}, dtype={frame.dtype}")
                
                # Stop camera
                camera.stop()
                print(f"✓ Camera stopped successfully")
                
                return True
                
            except Exception as e:
                print(f"✗ {config_name} configuration failed: {e}")
                continue
        
        print("✗ All configurations failed")
        return False
        
    except ImportError as e:
        print(f"✗ Failed to import picamera2: {e}")
        print("Make sure you're running this on a Raspberry Pi with picamera2 installed")
        return False
    except Exception as e:
        print(f"✗ Camera test failed: {e}")
        return False
    finally:
        try:
            camera.close()
        except:
            pass

def check_system_info():
    """Check system information"""
    print("=== System Information ===")
    try:
        import platform
        print(f"Platform: {platform.platform()}")
        print(f"Python version: {sys.version}")
        
        # Check if running on Raspberry Pi
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                if 'BCM' in cpuinfo or 'Raspberry Pi' in cpuinfo:
                    print("✓ Running on Raspberry Pi")
                else:
                    print("⚠ Not running on Raspberry Pi - picamera2 may not work")
        except:
            print("⚠ Cannot determine if running on Raspberry Pi")
            
    except Exception as e:
        print(f"Error getting system info: {e}")

if __name__ == "__main__":
    print("=== Picamera2 Diagnostic Test ===")
    check_system_info()
    print("\n=== Camera Test ===")
    success = test_camera()
    
    if success:
        print("\n✓ Camera test completed successfully!")
        print("Your camera should work with the main application.")
    else:
        print("\n✗ Camera test failed!")
        print("Please check:")
        print("1. Camera is connected properly")
        print("2. Camera is enabled: sudo raspi-config -> Interface Options -> Camera -> Enable")
        print("3. No other applications are using the camera")
        print("4. You're running on a Raspberry Pi")
        print("5. libcamera is properly installed: sudo apt install libcamera-tools")
