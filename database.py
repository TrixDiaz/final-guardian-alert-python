import firebase_admin
from firebase_admin import credentials, firestore
import json
from datetime import datetime
import uuid

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

def save_motion_detection(motion_data, confidence, captured_photo_path, device_serial="SNABC123", device_model="RPI3"):
    """Save motion detection data to Firebase Firestore"""
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

def save_face_detection(face_data, confidence, captured_photo_path, device_serial="SNABC123", device_model="RPI3"):
    """Save face detection data to Firebase Firestore"""
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

def get_users_with_faces():
    """Get all users with their face images from Firebase"""
    try:
        users_data = []
        
        # Get all users from the users collection
        users_ref = db.collection(USERS_COLLECTION)
        users = users_ref.stream()
        
        for user_doc in users:
            user_data = user_doc.to_dict()
            user_id = user_doc.id
            
            # Check if user has images field and it's not empty
            if 'images' in user_data and user_data['images']:
                # Ensure images is a list
                if isinstance(user_data['images'], str):
                    try:
                        images = json.loads(user_data['images'])
                    except:
                        continue
                else:
                    images = user_data['images']
                
                if len(images) > 0:
                    # Get firstName and lastName for face recognition name
                    first_name = user_data.get('firstName', '')
                    last_name = user_data.get('lastName', '')
                    
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
                        'images': images,
                        'total_images': len(images)
                    })
        
        return users_data
        
    except Exception as e:
        print(f"Error getting users from Firebase: {e}")
        return []
