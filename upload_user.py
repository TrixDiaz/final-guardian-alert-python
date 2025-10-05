import firebase_admin
from firebase_admin import credentials, firestore
import json
import base64
import uuid
from datetime import datetime
import os

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        # Check if Firebase app is already initialized
        if not firebase_admin._apps:
            cred = credentials.Certificate('firebase-config.json')
            firebase_admin.initialize_app(cred)
            print("Firebase Admin SDK initialized successfully")
        else:
            print("Firebase Admin SDK already initialized")
        return True
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        return False

def encode_image_to_base64(image_path):
    """Convert image file to base64 string"""
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return encoded_string
    except Exception as e:
        print(f"Error encoding image to base64: {e}")
        return None

def upload_user_to_firebase(first_name, last_name, image_paths=None):
    """Upload user data to Firebase users collection"""
    try:
        # Initialize Firebase
        if not initialize_firebase():
            return None
        
        # Get Firestore client
        db = firestore.client()
        
        # Generate random UID
        user_uid = str(uuid.uuid4())
        print(f"Generated UID: {user_uid}")
        
        # Prepare user data
        user_data = {
            'uid': user_uid,
            'firstName': first_name,
            'lastName': last_name,
            'email': f"{first_name.lower()}.{last_name.lower()}@example.com",
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Process multiple images if provided
        if image_paths:
            images_array = []
            for i, image_path in enumerate(image_paths):
                if os.path.exists(image_path):
                    print(f"Processing image {i+1}: {image_path}")
                    base64_image = encode_image_to_base64(image_path)
                    
                    if base64_image:
                        images_array.append({
                            'data': base64_image,
                            'format': 'base64',
                            'uploaded_at': datetime.utcnow(),
                            'filename': os.path.basename(image_path)
                        })
                        print(f"Image {i+1} encoded to base64 successfully")
                    else:
                        print(f"Failed to encode image {i+1} to base64")
                else:
                    print(f"Image {i+1} file not found: {image_path}")
            
            user_data['images'] = images_array
            print(f"Total images processed: {len(images_array)}")
        else:
            print("No images provided")
            # Add empty images array
            user_data['images'] = []
        
        # Upload to Firebase
        doc_ref = db.collection('users').document(user_uid)
        doc_ref.set(user_data)
        
        print(f"User uploaded successfully to Firebase!")
        print(f"UID: {user_uid}")
        print(f"Name: {first_name} {last_name}")
        print(f"Email: {user_data['email']}")
        print(f"Images count: {len(user_data['images'])}")
        
        # Show details of uploaded images
        if user_data['images']:
            print("Uploaded images:")
            for i, img in enumerate(user_data['images']):
                data_length = len(img['data']) if img['data'] else 0
                print(f"  {i+1}. {img.get('filename', 'Unknown')} - {data_length} characters")
        
        return {
            'success': True,
            'uid': user_uid,
            'data': user_data
        }
        
    except Exception as e:
        print(f"Error uploading user to Firebase: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

def main():
    """Main function to upload user data"""
    print("=== Firebase User Upload Script ===")
    
    # User data
    first_name = "Trix"
    last_name = "Darlucio"
    
    # Check if there are images in the dataset folder
    dataset_folder = "dataset/folder"
    image_files = []
    
    if os.path.exists(dataset_folder):
        for file in os.listdir(dataset_folder):
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                image_files.append(os.path.join(dataset_folder, file))
    
    print(f"Found {len(image_files)} image files in dataset folder")
    
    # Use all images if available, otherwise upload without images
    if image_files:
        print(f"Using all {len(image_files)} images:")
        for i, img in enumerate(image_files):
            print(f"  {i+1}. {img}")
    else:
        print("No images found, uploading user without images")
    
    # Upload user to Firebase
    result = upload_user_to_firebase(first_name, last_name, image_files)
    
    if result and result['success']:
        print("\n[SUCCESS] User uploaded successfully!")
        print(f"UID: {result['uid']}")
    else:
        print("\n[ERROR] Failed to upload user")
        if result:
            print(f"Error: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()
