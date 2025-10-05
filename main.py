import cv2
import numpy as np
import threading
import time
import base64
import os
import pickle
from datetime import datetime
from flask import Flask, Response, jsonify
from database import save_motion_detection, save_face_detection, get_firebase_upload_status
import face_recognition

# This project requires Picamera2 (libcamera) and will not fall back to other
# camera implementations. If importing Picamera2 fails, the Python import
# itself will raise an ImportError so the user can install the dependency.
from picamera2 import Picamera2

# Global device configuration
DEVICE_SERIAL_NUMBER = "SNABC123"
DEVICE_MODEL = "RPI3"

class FaceMotionDetector:
    def __init__(self):
        # Initialize camera flag
        self.camera_initialized = False
        self.camera = None
        
        # Initialize PiCamera2 for Raspberry Pi 5 with Camera Module 3
        print("Initializing Raspberry Pi 5 Camera Module 3...")
        
        try:
            # Initialize PiCamera2 with optimized settings for RPi 5 and Camera Module 3
            self.camera = Picamera2()
            
            # Create configuration optimized for RPi 5 and Camera Module 3
            self.camera_config = self.camera.create_video_configuration(
                main={"size": (640, 480), "format": "RGB888"},
                lores={"size": (320, 240), "format": "YUV420"}
            )
            
            # Configure and start camera
            self.camera.configure(self.camera_config)
            self.camera.start()
            self.camera_initialized = True
            print("✓ Raspberry Pi 5 Camera Module 3 initialized successfully!")
            
        except Exception as e:
            print(f"✗ Failed to initialize Raspberry Pi 5 Camera Module 3: {e}")
            print("Please check:")
            print("1. Camera Module 3 is connected properly to the camera connector")
            print("2. Camera is enabled: sudo raspi-config -> Interface Options -> Camera -> Enable")
            print("3. No other applications are using the camera")
            print("4. You're running on a Raspberry Pi 5")
            print("5. libcamera is installed: sudo apt install libcamera-tools")
            print("6. Camera Module 3 is compatible with RPi 5")
            self.camera_initialized = False
        
        # Load Haar cascade for face detection
        cascade_path = os.path.join("model", "haarcascade_frontalface_default.xml")
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Motion detection variables - High sensitivity settings
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=True,
            varThreshold=16,  # Lower threshold for more sensitivity
            history=500       # Longer history for better background learning
        )
        self.motion_detected = False
        self.motion_timer = 0
        self.motion_display_duration = 3  # seconds
        
        # Additional motion detection variables
        self.previous_frame = None
        self.motion_sensitivity = 30  # Lower = more sensitive
        self.min_motion_area = 200    # Minimum area to trigger motion
        
        # Frame for streaming
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
        # Motion detection storage
        self.last_motion_time = 0
        self.motion_cooldown = 30  # seconds between motion detections
        self.captures_dir = "captures"
        if not os.path.exists(self.captures_dir):
            os.makedirs(self.captures_dir)
        
        # Face recognition variables
        self.known_encodings = []
        self.known_names = []
        self.face_recognition_enabled = False
        self.last_face_detection_time = 0
        self.face_detection_cooldown = 30  # seconds between face detections
        self.load_face_encodings()
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self.process_frames)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def process_frames(self):
        """Main processing loop for face detection and motion detection"""
        while True:
            try:
                # Check if camera is initialized
                if not self.camera_initialized or self.camera is None:
                    print("Camera not initialized, skipping frame processing...")
                    time.sleep(1)
                    continue
                
                # Capture frame from PiCamera2
                frame = self.camera.capture_array()
                
                # Convert RGB to BGR for OpenCV
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Process frame for face detection and motion detection
                processed_frame = self.detect_faces_and_motion(frame_bgr)
                
                # Apply face recognition
                processed_frame = self.recognize_faces(processed_frame)
                
                # Update current frame for streaming
                with self.frame_lock:
                    self.current_frame = processed_frame
                    
            except Exception as e:
                print(f"Error processing frame: {e}")
                time.sleep(0.1)
    
    def detect_faces_and_motion(self, frame):
        """Detect faces and motion in the frame"""
        # Face detection (no drawing - handled by face recognition)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(30, 30)
        )
        
        # Motion detection with high sensitivity
        motion_mask = self.background_subtractor.apply(frame)
        
        # Apply morphological operations to reduce noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_OPEN, kernel)
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_CLOSE, kernel)
        
        # Additional frame difference method for extra sensitivity
        motion_detected = False
        if self.previous_frame is not None:
            # Convert current frame to grayscale
            gray_current = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_previous = cv2.cvtColor(self.previous_frame, cv2.COLOR_BGR2GRAY)
            
            # Calculate frame difference
            frame_diff = cv2.absdiff(gray_current, gray_previous)
            _, thresh = cv2.threshold(frame_diff, self.motion_sensitivity, 255, cv2.THRESH_BINARY)
            
            # Find contours in frame difference
            diff_contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Check frame difference for motion
            for contour in diff_contours:
                if cv2.contourArea(contour) > self.min_motion_area:
                    motion_detected = True
                    break
        
        # Update previous frame
        self.previous_frame = frame.copy()
        
        # Also check background subtractor method
        motion_contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Check for significant motion with lower threshold for higher sensitivity
        total_motion_area = 0
        for contour in motion_contours:
            area = cv2.contourArea(contour)
            if area > self.min_motion_area:  # Use configurable threshold
                total_motion_area += area
                motion_detected = True
        
        # Additional check: if total motion area is significant, trigger
        if total_motion_area > 1000:  # Total area threshold for large movements
            motion_detected = True
        
        # Update motion status and capture photo if motion detected
        current_time = time.time()
        if motion_detected:
            self.motion_detected = True
            self.motion_timer = current_time
            
            # Check both motion cooldown and Firebase upload status
            motion_cooldown_passed = current_time - self.last_motion_time > self.motion_cooldown
            firebase_status = get_firebase_upload_status()
            firebase_ready = firebase_status['can_upload_now']
            
            # Only capture photo if both conditions are met
            if motion_cooldown_passed and firebase_ready:
                self.capture_motion_photo(frame, total_motion_area)
                self.last_motion_time = current_time
            elif motion_cooldown_passed and not firebase_ready:
                remaining_firebase_delay = firebase_status['remaining_delay']
                print(f"Motion detected but Firebase upload delayed by {remaining_firebase_delay:.1f} seconds")
        elif current_time - self.motion_timer > self.motion_display_duration:
            self.motion_detected = False
        
        # Display motion text in upper right corner
        if self.motion_detected:
            cv2.putText(frame, 'Motion', (frame.shape[1] - 120, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        return frame
    
    def capture_motion_photo(self, frame, motion_area):
        """Capture photo when motion is detected and save to database"""
        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"motion_{timestamp}.jpg"
            
            # Save locally first
            local_filepath = os.path.join(self.captures_dir, filename)
            cv2.imwrite(local_filepath, frame)
            
            # Encode image as base64 for database storage
            _, buffer = cv2.imencode('.jpg', frame)
            image_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Calculate confidence based on motion area
            confidence = min(100, max(0, (motion_area / 1000) * 100))
            
            # Prepare motion data
            motion_data = {
                "motion_area": str(motion_area),
                "timestamp": timestamp,
                "sensitivity": self.motion_sensitivity,
                "min_area": self.min_motion_area
            }
            
            # Save to database with base64 image data
            result = save_motion_detection(
                motion_data=str(motion_data),
                confidence=str(confidence),
                captured_photo_path=image_base64,  # Store base64 image data
                device_serial=DEVICE_SERIAL_NUMBER,
                device_model=DEVICE_MODEL
            )
            
            if result:
                print(f"Motion detected and saved: {filename} (Area: {motion_area}, Confidence: {confidence:.1f}%)")
            else:
                print(f"Failed to save motion detection to database: {filename}")
                
        except Exception as e:
            print(f"Error capturing motion photo: {e}")
    
    def load_face_encodings(self):
        """Load face encodings from pickle file"""
        try:
            if os.path.exists("encodings.pickle"):
                with open("encodings.pickle", "rb") as f:
                    data = pickle.load(f)
                    self.known_encodings = data.get('encodings', [])
                    self.known_names = data.get('names', [])
                    self.face_recognition_enabled = len(self.known_encodings) > 0
                    print(f"Loaded {len(self.known_encodings)} face encodings for {len(set(self.known_names))} users")
                return True
            else:
                print("No encodings.pickle file found. Face recognition disabled.")
                return False
        except Exception as e:
            print(f"Error loading face encodings: {e}")
            return False
    
    def recognize_faces(self, frame):
        """Recognize faces in the frame"""
        if not self.face_recognition_enabled:
            return frame
        
        try:
            # Convert BGR to RGB for face_recognition
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Find face locations and encodings
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                # Compare with known faces
                # Lower tolerance = stricter matching (default is 0.6, using 0.5 for better accuracy)
                matches = face_recognition.compare_faces(self.known_encodings, face_encoding, tolerance=0.5)
                name = "Unknown"
                confidence = 0.0
                
                if True in matches:
                    # Find the best match
                    face_distances = face_recognition.face_distance(self.known_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    
                    # Only accept match if confidence is above 60%
                    if matches[best_match_index]:
                        confidence = (1 - face_distances[best_match_index]) * 100
                        if confidence >= 60.0:
                            name = self.known_names[best_match_index]
                        else:
                            name = "Unknown"
                
                # Draw rectangle and label
                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                
                # Draw label background
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                
                # Draw label text
                label = f"{name} ({confidence:.1f}%)" if name != "Unknown" else "Unknown"
                cv2.putText(frame, label, (left + 6, bottom - 6), 
                           cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
                
                # Save face detection to database (with cooldown and Firebase delay check)
                current_time = time.time()
                face_cooldown_passed = current_time - self.last_face_detection_time > self.face_detection_cooldown
                firebase_status = get_firebase_upload_status()
                firebase_ready = firebase_status['can_upload_now']
                
                # Only save face detection if both conditions are met
                if face_cooldown_passed and firebase_ready:
                    self.save_face_detection(frame, name, confidence, (left, top, right, bottom))
                    self.last_face_detection_time = current_time
                elif face_cooldown_passed and not firebase_ready:
                    remaining_firebase_delay = firebase_status['remaining_delay']
                    print(f"Face detected ({name}) but Firebase upload delayed by {remaining_firebase_delay:.1f} seconds")
            
            return frame
            
        except Exception as e:
            print(f"Error in face recognition: {e}")
            return frame
    
    def save_face_detection(self, frame, name, confidence, face_location):
        """Save face detection to database"""
        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"face_{name}_{timestamp}.jpg"
            
            # Save locally first
            local_filepath = os.path.join(self.captures_dir, filename)
            cv2.imwrite(local_filepath, frame)
            
            # Encode image as base64 for database storage
            _, buffer = cv2.imencode('.jpg', frame)
            image_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Prepare face data
            face_data = {
                "name": name,
                "confidence": confidence,
                "timestamp": timestamp,
                "face_location": face_location,
                "recognition_type": "known" if name != "Unknown" else "unknown"
            }
            
            # Save to database with base64 image data
            result = save_face_detection(
                face_data=str(face_data),
                confidence=str(confidence),
                captured_photo_path=image_base64,  # Store base64 image data
                device_serial=DEVICE_SERIAL_NUMBER,
                device_model=DEVICE_MODEL
            )
            
            if result:
                print(f"Face detected and saved: {name} (Confidence: {confidence:.1f}%)")
            else:
                print(f"Failed to save face detection to database: {name}")
                
        except Exception as e:
            print(f"Error saving face detection: {e}")
    
    def get_frame(self):
        """Get current frame for streaming"""
        with self.frame_lock:
            if self.current_frame is not None:
                # Encode frame as JPEG
                _, buffer = cv2.imencode('.jpg', self.current_frame)
                return buffer.tobytes()
        return None

# Initialize detector
detector = FaceMotionDetector()

# Flask app
app = Flask(__name__)

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    def generate():
        while True:
            frame = detector.get_frame()
            if frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.033)  # ~30 FPS
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("Starting Face Detection & Motion Sensor Application for Raspberry Pi 5...")
    print("Features:")
    print("- Raspberry Pi 5 with Camera Module 3 support")
    print("- Face detection with green bounding boxes")
    print("- Face recognition with known/unknown user identification")
    print("- High-sensitivity motion detection with red 'Motion' text in upper right")
    print("- Automatic photo capture and database storage on motion detection")
    print("- Automatic face recognition and database storage")
    print("- Flask web server for camera streaming")
    print("- 30-second Firebase upload delay to prevent spam")
    print("\nAccess URLs:")
    print("- Video stream: http://[PI_IP]:5000/video_feed")
    print(f"- Device Serial: {DEVICE_SERIAL_NUMBER}, Model: {DEVICE_MODEL}")
    print("\nTo sync user dataset, run: python sync_dataset.py")
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
        if detector.camera:
            detector.camera.stop()
            detector.camera.close()