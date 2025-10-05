import firebase_admin
from firebase_admin import credentials, firestore
import json
from datetime import datetime
import uuid
import time
import threading

# Initialize Firebase Admin SDK
try:
    # Check if Firebase app is already initialized
    if not firebase_admin._apps:
        cred = credentials.Certificate('firebase-config.json')
        firebase_admin.initialize_app(cred)
        print("Firebase Admin SDK initialized successfully")
    else:
        print("Firebase Admin SDK already initialized")
except Exception as e:
    print(f"Error initializing Firebase: {e}")

# Get Firestore client
db = firestore.client()

# Collection names
MOTION_DETECTION_COLLECTION = 'motion_detection'
FACE_DETECTION_COLLECTION = 'face_detection'
USERS_COLLECTION = 'users'

# Firebase upload delay tracking
last_firebase_upload_time = 0
FIREBASE_UPLOAD_DELAY = 30  # 30 seconds delay between Firebase uploads

def save_motion_detection(motion_data, confidence, captured_photo_path, device_serial="SNABC123", device_model="RPI3"):
    """Save motion detection data to Firebase Firestore with 30-second delay"""
    global last_firebase_upload_time
    
    def delayed_upload():
        """Perform the actual Firebase upload after delay"""
        try:
            # Generate unique ID
            detection_id = str(uuid.uuid4())
            
            # Prepare document data
            doc_data = {
                'id': detection_id,
                'motion_data': motion_data,
                'confidence': confidence,
                'captured_photo': captured_photo_path,
                'device_serial_number': device_serial,
                'device_model': device_model,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # Save to Firestore
            doc_ref = db.collection(MOTION_DETECTION_COLLECTION).document(detection_id)
            doc_ref.set(doc_data)
            
            print(f"Motion detection saved to Firebase: {detection_id}")
            return doc_data
            
        except Exception as e:
            print(f"Error saving motion detection to Firebase: {e}")
            return None
    
    try:
        current_time = time.time()
        
        # Check if enough time has passed since last upload
        if current_time - last_firebase_upload_time >= FIREBASE_UPLOAD_DELAY:
            # Upload immediately
            result = delayed_upload()
            last_firebase_upload_time = current_time
            return result
        else:
            # Calculate remaining delay time
            remaining_delay = FIREBASE_UPLOAD_DELAY - (current_time - last_firebase_upload_time)
            print(f"Firebase upload delayed by {remaining_delay:.1f} seconds to respect 30-second cooldown")
            
            # Schedule upload in a separate thread after the remaining delay
            def scheduled_upload():
                time.sleep(remaining_delay)
                result = delayed_upload()
                global last_firebase_upload_time
                last_firebase_upload_time = time.time()
                return result
            
            # Start the delayed upload in a separate thread
            upload_thread = threading.Thread(target=scheduled_upload)
            upload_thread.daemon = True
            upload_thread.start()
            
            return {"status": "scheduled", "delay_seconds": remaining_delay}
            
    except Exception as e:
        print(f"Error in motion detection delay logic: {e}")
        return None

def save_face_detection(face_data, confidence, captured_photo_path, device_serial="SNABC123", device_model="RPI3"):
    """Save face detection data to Firebase Firestore with 30-second delay"""
    global last_firebase_upload_time
    
    def delayed_upload():
        """Perform the actual Firebase upload after delay"""
        try:
            # Generate unique ID
            detection_id = str(uuid.uuid4())
            
            # Prepare document data
            doc_data = {
                'id': detection_id,
                'face_data': face_data,
                'confidence': confidence,
                'captured_photo': captured_photo_path,
                'device_serial_number': device_serial,
                'device_model': device_model,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # Save to Firestore
            doc_ref = db.collection(FACE_DETECTION_COLLECTION).document(detection_id)
            doc_ref.set(doc_data)
            
            print(f"Face detection saved to Firebase: {detection_id}")
            return doc_data
            
        except Exception as e:
            print(f"Error saving face detection to Firebase: {e}")
            return None
    
    try:
        current_time = time.time()
        
        # Check if enough time has passed since last upload
        if current_time - last_firebase_upload_time >= FIREBASE_UPLOAD_DELAY:
            # Upload immediately
            result = delayed_upload()
            last_firebase_upload_time = current_time
            return result
        else:
            # Calculate remaining delay time
            remaining_delay = FIREBASE_UPLOAD_DELAY - (current_time - last_firebase_upload_time)
            print(f"Firebase upload delayed by {remaining_delay:.1f} seconds to respect 30-second cooldown")
            
            # Schedule upload in a separate thread after the remaining delay
            def scheduled_upload():
                time.sleep(remaining_delay)
                result = delayed_upload()
                global last_firebase_upload_time
                last_firebase_upload_time = time.time()
                return result
            
            # Start the delayed upload in a separate thread
            upload_thread = threading.Thread(target=scheduled_upload)
            upload_thread.daemon = True
            upload_thread.start()
            
            return {"status": "scheduled", "delay_seconds": remaining_delay}
            
    except Exception as e:
        print(f"Error in face detection delay logic: {e}")
        return None

def get_users_with_faces():
    """Get all users with their face images from Firebase"""
    try:
        users_data = []
        
        # Get all users from the users collection
        users_ref = db.collection(USERS_COLLECTION)
        users = users_ref.stream()
        
        print(f"Fetching users from Firebase collection: {USERS_COLLECTION}")
        
        for user_doc in users:
            user_data = user_doc.to_dict()
            user_id = user_doc.id
            
            print(f"Processing user: {user_id}")
            print(f"User data keys: {list(user_data.keys())}")
            
            # Check if user has images field and it's not empty
            if 'images' in user_data and user_data['images']:
                print(f"Found images field for user {user_id}")
                
                # Ensure images is a list
                if isinstance(user_data['images'], str):
                    try:
                        images = json.loads(user_data['images'])
                        print(f"Parsed images from JSON string: {len(images)} items")
                    except Exception as e:
                        print(f"Error parsing images JSON for user {user_id}: {e}")
                        continue
                else:
                    images = user_data['images']
                    print(f"Images is already a list: {len(images)} items")
                
                if len(images) > 0:
                    # Convert base64 images to URLs for download
                    image_urls = []
                    for i, image_item in enumerate(images):
                        if isinstance(image_item, dict) and 'data' in image_item:
                            # This is base64 data, we'll need to save it directly
                            image_urls.append(image_item['data'])
                            print(f"Found base64 image {i+1} for user {user_id}")
                        elif isinstance(image_item, str):
                            # This might be a URL or base64 string
                            image_urls.append(image_item)
                            print(f"Found string image {i+1} for user {user_id}")
                        else:
                            print(f"Unknown image format for user {user_id}, item {i+1}: {type(image_item)}")
                    
                    if len(image_urls) > 0:
                        # Get firstName and lastName for face recognition name
                        first_name = user_data.get('firstName', '')
                        last_name = user_data.get('lastName', '')
                        
                        print(f"User {user_id}: firstName='{first_name}', lastName='{last_name}'")
                        
                        # Use firstName + lastName as the name for face recognition
                        if first_name and last_name:
                            full_name = f"{first_name} {last_name}"
                        elif first_name:
                            full_name = first_name
                        elif last_name:
                            full_name = last_name
                        else:
                            full_name = user_data.get('name', f"User_{user_id}")
                        
                        users_data.append({
                            'user_id': user_id,
                            'name': full_name,
                            'firstName': first_name,
                            'lastName': last_name,
                            'email': user_data.get('email', ''),
                            'images': image_urls,  # Use processed image URLs
                            'total_images': len(image_urls)
                        })
                        
                        print(f"Added user {full_name} with {len(image_urls)} images")
                    else:
                        print(f"No valid images found for user {user_id}")
                else:
                    print(f"Images array is empty for user {user_id}")
            else:
                print(f"No images field found for user {user_id}")
        
        print(f"Total users with face data: {len(users_data)}")
        return users_data
        
    except Exception as e:
        print(f"Error getting users from Firebase: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_firebase_upload_status():
    """Get current Firebase upload status and delay information"""
    global last_firebase_upload_time
    
    current_time = time.time()
    time_since_last_upload = current_time - last_firebase_upload_time
    remaining_delay = max(0, FIREBASE_UPLOAD_DELAY - time_since_last_upload)
    
    return {
        "last_upload_time": last_firebase_upload_time,
        "time_since_last_upload": time_since_last_upload,
        "remaining_delay": remaining_delay,
        "can_upload_now": remaining_delay <= 0,
        "upload_delay_seconds": FIREBASE_UPLOAD_DELAY
    }
